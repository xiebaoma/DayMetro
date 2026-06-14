extends Node2D

@export var backend_base_url := "http://127.0.0.1:8000"
@export var location_name := "宿舍"
@export var next_scene_path := "res://scenes/Metro.tscn"
@export var next_location_name := "地铁"
@export var enter_event_type := "enter_location"
@export var leave_event_type := "leave_location"
@export var arrive_next_event_type := "arrive_next_location"
@export var npc_display_name := "NPC"
@export var start_minutes := 420
@export var enter_player_action := ""
@export var generate_daily_review_on_enter := false

var _minutes := 420
var _tick_accumulator := 0.0
var _is_near_npc := false
var _is_transitioning := false
var _active_npc: Dictionary = {}
var _npc_areas: Array[Area2D] = []
var _dialogue_options: Array = []
var _selected_option_index := 0
var _rng := RandomNumberGenerator.new()
var _proactive_timer := 0.0
var _proactive_request_in_flight := false
var _proactive_lines: Dictionary = {}

@onready var _player: CharacterBody2D = $Player
@onready var _time_label: Label = $CanvasLayer/HUD/TimeLabel
@onready var _location_label: Label = $CanvasLayer/HUD/LocationLabel
@onready var _state_label: Label = $CanvasLayer/HUD/PlayerStateLabel
@onready var _hint_label: Label = $CanvasLayer/HUD/HintLabel
@onready var _dialogue_panel: PanelContainer = $CanvasLayer/HUD/DialoguePanel
@onready var _dialogue_label: Label = $CanvasLayer/HUD/DialoguePanel/DialogueText
@onready var _npc_area: Area2D = $NpcArea
@onready var _npc_collision: CollisionShape2D = $NpcArea/CollisionShape2D
@onready var _exit_area: Area2D = $ExitArea
@onready var _event_request: HTTPRequest = $EventRequest
@onready var _world_state_request: HTTPRequest = $WorldStateRequest

var _dialogue_options_request: HTTPRequest
var _dialogue_choice_request: HTTPRequest
var _player_action_request: HTTPRequest
var _daily_review_request: HTTPRequest
var _proactive_request: HTTPRequest


func _ready() -> void:
	_rng.randomize()
	_dialogue_options_request = HTTPRequest.new()
	_dialogue_choice_request = HTTPRequest.new()
	_player_action_request = HTTPRequest.new()
	_daily_review_request = HTTPRequest.new()
	_proactive_request = HTTPRequest.new()
	add_child(_dialogue_options_request)
	add_child(_dialogue_choice_request)
	add_child(_player_action_request)
	add_child(_daily_review_request)
	add_child(_proactive_request)

	_prepare_layering()
	_build_scene_dressing()
	_npc_areas = [_npc_area]
	_build_npc_sprite(_npc_area)

	# Exit visual marker
	var exit_marker := Polygon2D.new()
	exit_marker.name = "ExitMarker"
	exit_marker.polygon = PackedVector2Array([
		Vector2(-22, -56), Vector2(6, -56), Vector2(6, -22),
		Vector2(24, -22), Vector2(24, 22), Vector2(6, 22),
		Vector2(6, 56), Vector2(-22, 56)
	])
	exit_marker.color = Color(0.18, 0.95, 0.54, 0.28)
	_exit_area.add_child(exit_marker)

	var exit_label := Label.new()
	exit_label.name = "ExitLabel"
	exit_label.text = "→ 出口"
	exit_label.add_theme_font_size_override("font_size", 12)
	exit_label.add_theme_color_override("font_color", Color.GREEN)
	exit_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	exit_label.size = Vector2(48, 20)
	exit_label.position = Vector2(-24, -10)
	_exit_area.add_child(exit_label)

	# Ensure background fills screen
	var bg = get_node_or_null("Background")
	if bg is ColorRect:
		bg.size = get_viewport().get_visible_rect().size

	_minutes = start_minutes
	_schedule_next_proactive_chat()
	_npc_area.body_entered.connect(_on_npc_body_entered.bind(_npc_area))
	_npc_area.body_exited.connect(_on_npc_body_exited.bind(_npc_area))
	_exit_area.body_entered.connect(_on_exit_body_entered)
	_hint_label.text = ""
	_dialogue_panel.visible = false
	_update_hud()
	_post_event(enter_event_type, location_name)
	if enter_player_action != "":
		await _post_player_action(enter_player_action, location_name)
	_sync_world_state()
	if generate_daily_review_on_enter:
		await _generate_daily_review()
	else:
		_request_proactive_lines()


func _prepare_layering() -> void:
	var bg = get_node_or_null("Background")
	if bg is CanvasItem:
		bg.z_index = -100
	_player.z_index = 20
	_npc_area.z_index = 18
	_exit_area.z_index = 12


func _build_scene_dressing() -> void:
	if get_node_or_null("SceneDressing") != null:
		return

	var dressing := Node2D.new()
	dressing.name = "SceneDressing"
	dressing.z_index = -20
	add_child(dressing)
	move_child(dressing, 1)

	_add_location_title(dressing)
	match location_name:
		"宿舍":
			_build_dorm_details(dressing)
		"地铁":
			_build_metro_details(dressing)
		"公司":
			_build_company_details(dressing)
		"食堂":
			_build_canteen_details(dressing)
		"操场":
			_build_playground_details(dressing)


func _add_location_title(parent: Node2D) -> void:
	var plate := ColorRect.new()
	plate.name = "LocationPlate"
	plate.position = Vector2(876, 26)
	plate.size = Vector2(360, 86)
	plate.color = Color(0.02, 0.025, 0.03, 0.56)
	parent.add_child(plate)

	var title := Label.new()
	title.name = "BigLocationTitle"
	title.text = location_name
	title.position = Vector2(900, 35)
	title.size = Vector2(320, 44)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	title.add_theme_font_size_override("font_size", 36)
	title.add_theme_color_override("font_color", Color(1, 1, 1, 0.96))
	parent.add_child(title)

	var subtitle := Label.new()
	subtitle.name = "LocationSubtitle"
	subtitle.text = _location_subtitle()
	subtitle.position = Vector2(900, 78)
	subtitle.size = Vector2(320, 24)
	subtitle.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	subtitle.add_theme_font_size_override("font_size", 14)
	subtitle.add_theme_color_override("font_color", Color(0.82, 0.9, 0.94, 0.85))
	parent.add_child(subtitle)


func _location_subtitle() -> String:
	match location_name:
		"宿舍":
			if start_minutes >= 1200:
				return "夜晚复盘 · 回到床铺"
			return "清晨整理 · 室友和床铺"
		"地铁":
			return "通勤车厢 · 城市掠过窗外"
		"公司":
			if start_minutes >= 780:
				return "下午推进 · 工位和会议板"
			return "上午早会 · 开始工作"
		"食堂":
			return "午饭时间 · 餐盘和热汤"
		"操场":
			return "晚风散步 · 跑道和路灯"
	return "DayMetro"


func _build_dorm_details(parent: Node2D) -> void:
	if start_minutes >= 1200:
		_add_rect(parent, "NightOverlay", Vector2(0, 0), Vector2(1280, 720), Color(0.02, 0.03, 0.08, 0.36))
		_add_rect(parent, "PhoneGlow", Vector2(610, 398), Vector2(70, 32), Color(0.3, 0.55, 1.0, 0.42))
		_add_label(parent, "NightHint", "深夜宿舍", Vector2(508, 176), Vector2(260, 34), 24, Color(0.72, 0.82, 1.0, 0.86), HORIZONTAL_ALIGNMENT_CENTER)
	else:
		_add_rect(parent, "SunBeamWide", Vector2(520, 170), Vector2(390, 58), Color(1.0, 0.78, 0.36, 0.14))
		_add_rect(parent, "Books", Vector2(594, 220), Vector2(48, 12), Color(0.74, 0.18, 0.19, 1))
		_add_rect(parent, "BookPages", Vector2(596, 207), Vector2(44, 13), Color(0.95, 0.89, 0.72, 1))


func _build_metro_details(parent: Node2D) -> void:
	_add_rect(parent, "CarWall", Vector2(64, 92), Vector2(1152, 444), Color(0.72, 0.78, 0.8, 1))
	_add_rect(parent, "CarFloor", Vector2(64, 536), Vector2(1152, 94), Color(0.22, 0.25, 0.29, 1))
	_add_rect(parent, "WindowA", Vector2(156, 150), Vector2(245, 156), Color(0.12, 0.25, 0.38, 1))
	_add_rect(parent, "WindowB", Vector2(440, 150), Vector2(245, 156), Color(0.12, 0.25, 0.38, 1))
	_add_rect(parent, "WindowC", Vector2(724, 150), Vector2(245, 156), Color(0.12, 0.25, 0.38, 1))
	_add_rect(parent, "WindowD", Vector2(1008, 150), Vector2(132, 156), Color(0.12, 0.25, 0.38, 1))
	for x in [186, 312, 470, 604, 752, 890, 1036]:
		_add_rect(parent, "CityLight%s" % x, Vector2(x, 208 + (x % 3) * 22), Vector2(54, 8), Color(1.0, 0.78, 0.24, 0.55))
	for x in [240, 520, 800, 1080]:
		_add_rect(parent, "Seat%s" % x, Vector2(x, 388), Vector2(180, 82), Color(0.18, 0.38, 0.63, 1))
		_add_rect(parent, "SeatBack%s" % x, Vector2(x, 340), Vector2(180, 52), Color(0.22, 0.47, 0.76, 1))
	_add_rect(parent, "HandrailTop", Vector2(130, 116), Vector2(980, 10), Color(0.96, 0.78, 0.25, 1))
	for x in [220, 370, 520, 670, 820, 970]:
		_add_rect(parent, "HandleStrap%s" % x, Vector2(x, 126), Vector2(6, 74), Color(0.96, 0.78, 0.25, 1))
		_add_rect(parent, "Handle%s" % x, Vector2(x - 18, 196), Vector2(42, 8), Color(0.96, 0.78, 0.25, 1))
	_add_label(parent, "LineSign", "DAYMETRO  08:20 → 公司", Vector2(432, 48), Vector2(416, 34), 22, Color(0.98, 0.96, 0.8, 1), HORIZONTAL_ALIGNMENT_CENTER)


func _build_company_details(parent: Node2D) -> void:
	var evening := start_minutes >= 780
	_add_rect(parent, "OfficeFloor", Vector2(74, 430), Vector2(1132, 202), Color(0.34, 0.38, 0.36, 1))
	_add_rect(parent, "GlassWall", Vector2(74, 84), Vector2(1132, 220), Color(0.2, 0.32, 0.39, 1))
	for i in range(7):
		var x := 108 + i * 152
		_add_rect(parent, "WindowPane%s" % i, Vector2(x, 102), Vector2(118, 176), Color(0.36, 0.54, 0.62, 0.62))
		_add_rect(parent, "Building%s" % i, Vector2(x + 22, 160), Vector2(42, 94), Color(0.08, 0.13, 0.18, 0.45))
		if evening:
			_add_rect(parent, "EveningLight%s" % i, Vector2(x + 76, 130), Vector2(28, 12), Color(1.0, 0.72, 0.28, 0.62))
	_add_rect(parent, "Whiteboard", Vector2(820, 322), Vector2(260, 116), Color(0.92, 0.95, 0.9, 1))
	_add_label(parent, "BoardText", "Sprint / Review / Bug", Vector2(842, 352), Vector2(218, 24), 17, Color(0.16, 0.26, 0.24, 1), HORIZONTAL_ALIGNMENT_CENTER)
	for x in [196, 430, 664]:
		_add_rect(parent, "Desk%s" % x, Vector2(x, 350), Vector2(168, 76), Color(0.36, 0.29, 0.23, 1))
		_add_rect(parent, "Monitor%s" % x, Vector2(x + 52, 300), Vector2(72, 50), Color(0.05, 0.08, 0.1, 1))
		_add_rect(parent, "MonitorGlow%s" % x, Vector2(x + 58, 306), Vector2(60, 34), Color(0.2, 0.68, 0.72, 1))
		_add_rect(parent, "Chair%s" % x, Vector2(x + 62, 438), Vector2(48, 48), Color(0.12, 0.16, 0.19, 1))
	_add_label(parent, "OfficeSign", "OPEN OFFICE", Vector2(86, 320), Vector2(240, 32), 24, Color(0.9, 0.96, 0.9, 0.9), HORIZONTAL_ALIGNMENT_LEFT)


func _build_canteen_details(parent: Node2D) -> void:
	_add_rect(parent, "WarmWall", Vector2(72, 80), Vector2(1136, 230), Color(0.68, 0.43, 0.24, 1))
	_add_rect(parent, "TileFloor", Vector2(72, 310), Vector2(1136, 322), Color(0.58, 0.49, 0.38, 1))
	for y in [366, 442, 518, 594]:
		_add_rect(parent, "TileLineY%s" % y, Vector2(72, y), Vector2(1136, 4), Color(0.45, 0.38, 0.3, 0.5))
	for x in [204, 368, 532, 696, 860, 1024]:
		_add_rect(parent, "TileLineX%s" % x, Vector2(x, 310), Vector2(4, 322), Color(0.45, 0.38, 0.3, 0.35))
	for x in [150, 358, 566]:
		_add_rect(parent, "ServingWindow%s" % x, Vector2(x, 122), Vector2(168, 92), Color(0.9, 0.78, 0.54, 1))
		_add_rect(parent, "Counter%s" % x, Vector2(x - 10, 214), Vector2(188, 38), Color(0.36, 0.2, 0.12, 1))
		_add_rect(parent, "Steam%s" % x, Vector2(x + 52, 88), Vector2(14, 34), Color(1, 1, 1, 0.22))
		_add_rect(parent, "SteamB%s" % x, Vector2(x + 92, 82), Vector2(12, 40), Color(1, 1, 1, 0.18))
	for x in [226, 526, 826]:
		_add_rect(parent, "Table%s" % x, Vector2(x, 410), Vector2(210, 64), Color(0.55, 0.31, 0.16, 1))
		_add_rect(parent, "Tray%s" % x, Vector2(x + 64, 424), Vector2(80, 34), Color(0.9, 0.88, 0.72, 1))
		_add_rect(parent, "Soup%s" % x, Vector2(x + 86, 430), Vector2(30, 22), Color(0.78, 0.28, 0.16, 1))
	_add_label(parent, "CanteenSign", "今日午餐", Vector2(824, 140), Vector2(190, 40), 28, Color(1.0, 0.95, 0.74, 1), HORIZONTAL_ALIGNMENT_CENTER)


func _build_playground_details(parent: Node2D) -> void:
	_add_rect(parent, "Sky", Vector2(0, 0), Vector2(1280, 310), Color(0.05, 0.08, 0.17, 1))
	_add_rect(parent, "Grass", Vector2(0, 310), Vector2(1280, 410), Color(0.08, 0.28, 0.16, 1))
	for y in [365, 430, 495, 560]:
		_add_rect(parent, "TrackLane%s" % y, Vector2(72, y), Vector2(1136, 44), Color(0.48, 0.16, 0.12, 1))
		_add_rect(parent, "TrackLine%s" % y, Vector2(72, y), Vector2(1136, 3), Color(1, 0.94, 0.82, 0.72))
	_add_rect(parent, "InnerField", Vector2(260, 412), Vector2(760, 116), Color(0.1, 0.38, 0.18, 1))
	for x in [130, 1120]:
		_add_rect(parent, "LampPole%s" % x, Vector2(x, 118), Vector2(10, 232), Color(0.23, 0.25, 0.28, 1))
		_add_rect(parent, "LampHead%s" % x, Vector2(x - 32, 100), Vector2(74, 20), Color(0.95, 0.86, 0.54, 1))
		_add_rect(parent, "LampGlow%s" % x, Vector2(x - 95, 120), Vector2(200, 190), Color(1.0, 0.86, 0.4, 0.1))
	for x in [330, 480, 820, 980]:
		_add_rect(parent, "CampusBuilding%s" % x, Vector2(x, 168), Vector2(100, 112), Color(0.08, 0.1, 0.16, 0.82))
		_add_rect(parent, "DormLight%s" % x, Vector2(x + 20, 196), Vector2(16, 12), Color(1.0, 0.75, 0.28, 0.72))
		_add_rect(parent, "DormLightB%s" % x, Vector2(x + 58, 232), Vector2(16, 12), Color(1.0, 0.75, 0.28, 0.62))
	_add_label(parent, "TrackSign", "400m TRACK", Vector2(530, 588), Vector2(220, 30), 24, Color(1.0, 0.9, 0.75, 0.86), HORIZONTAL_ALIGNMENT_CENTER)


func _build_npc_sprite(area: Area2D) -> void:
	if area.get_node_or_null("NpcBody") != null:
		return

	var shadow := Polygon2D.new()
	shadow.name = "NpcShadow"
	shadow.polygon = _ellipse_points(Vector2(0, 22), 20, 7)
	shadow.color = Color(0.02, 0.02, 0.025, 0.3)
	area.add_child(shadow)

	var body := Polygon2D.new()
	body.name = "NpcBody"
	body.polygon = PackedVector2Array([
		Vector2(-17, -18), Vector2(17, -18), Vector2(22, 16), Vector2(-22, 16)
	])
	body.color = Color(0.95, 0.63, 0.18, 1)
	area.add_child(body)

	var badge := ColorRect.new()
	badge.name = "NpcBadge"
	badge.position = Vector2(-12, -8)
	badge.size = Vector2(24, 8)
	badge.color = Color(1, 0.95, 0.66, 1)
	area.add_child(badge)

	var head := Polygon2D.new()
	head.name = "NpcHead"
	head.polygon = _ellipse_points(Vector2(0, -34), 13, 14)
	head.color = Color(0.93, 0.7, 0.5, 1)
	area.add_child(head)

	var hair := Polygon2D.new()
	hair.name = "NpcHair"
	hair.polygon = PackedVector2Array([
		Vector2(-13, -39), Vector2(-4, -50), Vector2(10, -46),
		Vector2(15, -38), Vector2(7, -35), Vector2(-13, -35)
	])
	hair.color = Color(0.16, 0.1, 0.06, 1)
	area.add_child(hair)

	var npc_label := Label.new()
	npc_label.name = "NpcLabel"
	npc_label.text = "NPC"
	npc_label.add_theme_font_size_override("font_size", 11)
	npc_label.add_theme_color_override("font_color", Color.WHITE)
	npc_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	npc_label.size = Vector2(72, 18)
	npc_label.position = Vector2(-36, 24)
	area.add_child(npc_label)


func _ensure_npc_area_count(count: int) -> void:
	while _npc_areas.size() < count:
		var area := Area2D.new()
		area.name = "NpcArea%s" % (_npc_areas.size() + 1)
		area.z_index = 18
		add_child(area)

		var shape := CollisionShape2D.new()
		shape.name = "CollisionShape2D"
		var rect := RectangleShape2D.new()
		rect.size = Vector2(60, 60)
		shape.shape = rect
		area.add_child(shape)

		_build_npc_sprite(area)
		area.body_entered.connect(_on_npc_body_entered.bind(area))
		area.body_exited.connect(_on_npc_body_exited.bind(area))
		_npc_areas.append(area)


func _layout_npc_position(index: int, total: int) -> Vector2:
	if location_name == "宿舍":
		var dorm_positions := [
			Vector2(430, 360),
			Vector2(620, 390),
			Vector2(810, 360)
		]
		return dorm_positions[min(index, dorm_positions.size() - 1)]

	var center := Vector2(520, 340)
	if total == 1:
		return center
	return center + Vector2((index - (total - 1) * 0.5) * 140.0, 0)


func _wander_bounds() -> Rect2:
	match location_name:
		"宿舍":
			return Rect2(Vector2(180, 245), Vector2(870, 280))
		"地铁":
			return Rect2(Vector2(160, 335), Vector2(900, 145))
		"公司":
			return Rect2(Vector2(150, 330), Vector2(820, 180))
		"食堂":
			return Rect2(Vector2(150, 350), Vector2(840, 190))
		"操场":
			return Rect2(Vector2(120, 365), Vector2(980, 220))
	return Rect2(Vector2(120, 220), Vector2(980, 340))


func _clamp_to_wander_bounds(point: Vector2) -> Vector2:
	var bounds := _wander_bounds()
	return Vector2(
		clamp(point.x, bounds.position.x, bounds.position.x + bounds.size.x),
		clamp(point.y, bounds.position.y, bounds.position.y + bounds.size.y)
	)


func _make_initial_wander_state(home: Vector2) -> Dictionary:
	return {
		"home": home,
		"target": home,
		"wait_remaining": _rng.randf_range(0.8, 2.8),
		"speed": _rng.randf_range(34.0, 58.0),
		"leave_check_remaining": _rng.randf_range(18.0, 42.0),
	}


func _scene_exit_point() -> Vector2:
	match location_name:
		"宿舍":
			return Vector2(1078, 430)
		"地铁":
			return Vector2(1128, 410)
		"公司":
			return Vector2(1088, 430)
		"食堂":
			return Vector2(1090, 450)
		"操场":
			return Vector2(1135, 520)
	return Vector2(1120, 420)


func _scene_return_point() -> Vector2:
	return _clamp_to_wander_bounds(_scene_exit_point() + Vector2(-26, 0))


func _schedule_next_leave_check(area: Area2D) -> void:
	var state: Dictionary = area.get_meta("wander_state", _make_initial_wander_state(area.position))
	state["leave_check_remaining"] = _rng.randf_range(22.0, 55.0)
	area.set_meta("wander_state", state)


func _choose_next_wander_state(area: Area2D) -> void:
	var state: Dictionary = area.get_meta("wander_state", {})
	var home: Vector2 = state.get("home", area.position)
	state["speed"] = _rng.randf_range(30.0, 62.0)

	if _rng.randf() < 0.48:
		state["wait_remaining"] = _rng.randf_range(1.2, 4.4)
		state["target"] = area.position
	else:
		var radius := _rng.randf_range(55.0, 165.0)
		var angle := _rng.randf_range(0.0, TAU)
		var target := home + Vector2(cos(angle), sin(angle)) * radius
		state["target"] = _clamp_to_wander_bounds(target)
		state["wait_remaining"] = 0.0

	area.set_meta("wander_state", state)


func _stop_npc_at_current_position(area: Area2D) -> void:
	var state: Dictionary = area.get_meta("wander_state", _make_initial_wander_state(area.position))
	state["target"] = area.position
	state["wait_remaining"] = 9999.0
	area.set_meta("wander_state", state)


func _hold_npc_before_wandering(area: Area2D) -> void:
	var state: Dictionary = area.get_meta("wander_state", _make_initial_wander_state(area.position))
	state["target"] = area.position
	state["wait_remaining"] = _rng.randf_range(0.8, 2.2)
	area.set_meta("wander_state", state)


func _set_area_collision_enabled(area: Area2D, enabled: bool) -> void:
	var collision = area.get_node_or_null("CollisionShape2D")
	if collision is CollisionShape2D:
		collision.disabled = not enabled


func _add_rect(parent: Node2D, rect_name: String, position: Vector2, size: Vector2, color: Color) -> ColorRect:
	var rect := ColorRect.new()
	rect.name = rect_name
	rect.position = position
	rect.size = size
	rect.color = color
	parent.add_child(rect)
	return rect


func _add_label(parent: Node2D, label_name: String, text: String, position: Vector2, size: Vector2, font_size: int, color: Color, alignment: HorizontalAlignment) -> Label:
	var label := Label.new()
	label.name = label_name
	label.text = text
	label.position = position
	label.size = size
	label.horizontal_alignment = alignment
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", color)
	parent.add_child(label)
	return label


func _ellipse_points(center: Vector2, radius_x: float, radius_y: float) -> PackedVector2Array:
	var points := PackedVector2Array()
	for i in range(28):
		var angle := TAU * float(i) / 28.0
		points.append(center + Vector2(cos(angle) * radius_x, sin(angle) * radius_y))
	return points


func _process(delta: float) -> void:
	_tick_accumulator += delta
	if _tick_accumulator >= 1.0:
		_tick_accumulator = 0.0
		_minutes = min(_minutes + 5, 23 * 60 + 59)
		_update_hud()
	_update_proactive_chat(delta)
	_update_npc_wander(delta)


func _update_npc_wander(delta: float) -> void:
	for area in _npc_areas:
		if _update_npc_scene_presence(area, delta):
			continue
		if not area.visible:
			continue
		if str(area.get_meta("proactive_state", "idle")) == "approaching_player":
			_update_npc_approach_player(area, delta)
			continue
		if _should_pause_npc(area):
			continue

		var state: Dictionary = area.get_meta("wander_state", {})
		if state.is_empty():
			state = _make_initial_wander_state(area.position)
			area.set_meta("wander_state", state)

		_update_leave_check(area, state, delta)
		if str(area.get_meta("scene_presence", "present")) == "leaving_scene":
			continue

		var wait_remaining := float(state.get("wait_remaining", 0.0))
		if wait_remaining > 0.0:
			state["wait_remaining"] = max(0.0, wait_remaining - delta)
			area.set_meta("wander_state", state)
			if state["wait_remaining"] <= 0.0:
				_choose_next_wander_state(area)
			continue

		var target: Vector2 = state.get("target", area.position)
		var to_target := target - area.position
		if to_target.length() <= 3.0:
			state["wait_remaining"] = _rng.randf_range(1.0, 3.8)
			state["target"] = area.position
			area.set_meta("wander_state", state)
			continue

		var speed := float(state.get("speed", 42.0))
		var step: float = min(speed * delta, to_target.length())
		area.position = _clamp_to_wander_bounds(area.position + to_target.normalized() * step)


func _update_leave_check(area: Area2D, state: Dictionary, delta: float) -> void:
	if _dialogue_panel.visible or _is_near_npc:
		return
	if str(area.get_meta("proactive_state", "idle")) != "idle":
		return
	if str(area.get_meta("scene_presence", "present")) != "present":
		return

	var leave_check_remaining := float(state.get("leave_check_remaining", _rng.randf_range(18.0, 42.0)))
	leave_check_remaining -= delta
	if leave_check_remaining > 0.0:
		state["leave_check_remaining"] = leave_check_remaining
		area.set_meta("wander_state", state)
		return

	if _rng.randf() <= 0.34:
		_begin_scene_leave(area)
	else:
		_schedule_next_leave_check(area)


func _begin_scene_leave(area: Area2D) -> void:
	area.set_meta("scene_presence", "leaving_scene")
	var state: Dictionary = area.get_meta("wander_state", _make_initial_wander_state(area.position))
	state["target"] = _scene_exit_point()
	state["wait_remaining"] = 0.0
	state["speed"] = _rng.randf_range(54.0, 82.0)
	area.set_meta("wander_state", state)
	var npc_data: Variant = area.get_meta("npc_data", {})
	if typeof(npc_data) == TYPE_DICTIONARY:
		_hint_label.text = "%s 暂时离开了%s。" % [npc_data.get("name", "NPC"), location_name]


func _update_npc_scene_presence(area: Area2D, delta: float) -> bool:
	var presence := str(area.get_meta("scene_presence", "present"))
	if presence == "present":
		return false

	if presence == "leaving_scene":
		_move_area_toward(area, _scene_exit_point(), delta, 78.0)
		if area.position.distance_to(_scene_exit_point()) <= 6.0:
			area.set_meta("scene_presence", "off_scene")
			area.set_meta("off_scene_remaining", _rng.randf_range(5.0, 16.0))
			area.visible = false
			area.monitoring = false
			_set_area_collision_enabled(area, false)
			_refresh_location_hint()
		return true

	if presence == "off_scene":
		var remaining := float(area.get_meta("off_scene_remaining", 8.0)) - delta
		if remaining > 0.0:
			area.set_meta("off_scene_remaining", remaining)
			return true

		area.position = _scene_return_point()
		area.visible = true
		area.monitoring = true
		_set_area_collision_enabled(area, true)
		area.set_meta("scene_presence", "returning_scene")
		var npc_data: Variant = area.get_meta("npc_data", {})
		if typeof(npc_data) == TYPE_DICTIONARY:
			_hint_label.text = "%s 回到了%s。" % [npc_data.get("name", "NPC"), location_name]
		return true

	if presence == "returning_scene":
		var state: Dictionary = area.get_meta("wander_state", _make_initial_wander_state(area.position))
		var home: Vector2 = state.get("home", _layout_npc_position(0, 1))
		_move_area_toward(area, home, delta, 68.0)
		if area.position.distance_to(home) <= 8.0:
			area.set_meta("scene_presence", "present")
			state["target"] = area.position
			state["wait_remaining"] = _rng.randf_range(1.0, 3.0)
			state["home"] = area.position
			area.set_meta("wander_state", state)
			_schedule_next_leave_check(area)
			_refresh_location_hint()
		return true

	return false


func _move_area_toward(area: Area2D, target: Vector2, delta: float, speed: float) -> void:
	var to_target := target - area.position
	if to_target.length() <= 0.1:
		return
	var step: float = min(speed * delta, to_target.length())
	area.position += to_target.normalized() * step


func _update_npc_approach_player(area: Area2D, delta: float) -> void:
	if _dialogue_panel.visible:
		return

	var target := _clamp_to_wander_bounds(_player.global_position + Vector2(54, 0))
	var to_target := target - area.position
	if to_target.length() <= 18.0:
		_start_proactive_dialogue(area)
		return

	var step: float = min(82.0 * delta, to_target.length())
	area.position = _clamp_to_wander_bounds(area.position + to_target.normalized() * step)


func _update_proactive_chat(delta: float) -> void:
	if _dialogue_panel.visible or _is_near_npc or _proactive_request_in_flight:
		return
	if _has_active_proactive_approach():
		return

	_proactive_timer -= delta
	if _proactive_timer > 0.0:
		return

	var candidates := _available_proactive_npc_areas()
	if candidates.is_empty():
		_schedule_next_proactive_chat()
		return

	if _rng.randf() <= 0.62:
		var selected: Area2D = candidates[_rng.randi_range(0, candidates.size() - 1)]
		_begin_proactive_approach(selected)

	_schedule_next_proactive_chat()


func _schedule_next_proactive_chat() -> void:
	_proactive_timer = _rng.randf_range(12.0, 32.0)


func _available_proactive_npc_areas() -> Array[Area2D]:
	var result: Array[Area2D] = []
	for area in _npc_areas:
		if not area.visible:
			continue
		var npc_data: Variant = area.get_meta("npc_data", {})
		if typeof(npc_data) != TYPE_DICTIONARY:
			continue
		if str(area.get_meta("proactive_state", "idle")) != "idle":
			continue
		result.append(area)
	return result


func _has_active_proactive_approach() -> bool:
	for area in _npc_areas:
		if str(area.get_meta("proactive_state", "idle")) != "idle":
			return true
	return false


func _begin_proactive_approach(area: Area2D) -> void:
	area.set_meta("proactive_state", "approaching_player")
	_stop_npc_at_current_position(area)
	var npc_data: Variant = area.get_meta("npc_data", {})
	if typeof(npc_data) == TYPE_DICTIONARY:
		_hint_label.text = "%s 正朝你走过来。" % npc_data.get("name", "NPC")
	_request_proactive_lines()


func _start_proactive_dialogue(area: Area2D) -> void:
	var npc_data: Variant = area.get_meta("npc_data", {})
	if typeof(npc_data) != TYPE_DICTIONARY:
		area.set_meta("proactive_state", "idle")
		return

	area.set_meta("proactive_state", "talking")
	_active_npc = npc_data
	_is_near_npc = true
	npc_display_name = str(_active_npc.get("name", npc_display_name))
	_stop_npc_at_current_position(area)

	var npc_id := str(_active_npc.get("id", ""))
	var line := str(_proactive_lines.get(npc_id, _fallback_proactive_line(_active_npc)))
	_dialogue_options = []
	_selected_option_index = 0
	_dialogue_panel.visible = true
	_dialogue_label.text = "%s 主动走过来：%s\n\n按 Enter 回应，按 Esc 关闭。" % [
		npc_display_name,
		line
	]


func _fallback_proactive_line(npc_data: Dictionary) -> String:
	var current_action := str(npc_data.get("current_action", "忙自己的事"))
	var goal := str(npc_data.get("goal", "把今天过好"))
	return "我刚在%s，正好想问问你今天怎么样。我的目标是%s。" % [current_action, goal]


func _request_proactive_lines() -> void:
	if _proactive_request_in_flight:
		return
	_proactive_request_in_flight = true
	var url := "%s/npc/proactive?location=%s&limit=3" % [backend_base_url, location_name.uri_encode()]
	var err := _proactive_request.request(url)
	if err != OK:
		_proactive_request_in_flight = false
		return

	_parse_proactive_lines(await _proactive_request.request_completed)
	_proactive_request_in_flight = false


func _parse_proactive_lines(result: Array) -> void:
	if result.size() != 4:
		return
	var raw_body: PackedByteArray = result[3]
	if raw_body == null:
		return

	var parsed: Variant = JSON.parse_string(raw_body.get_string_from_utf8())
	if typeof(parsed) != TYPE_DICTIONARY:
		return

	var items: Array = parsed.get("proactive_actions", [])
	for item in items:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var npc_id := str(item.get("npc_id", ""))
		if npc_id == "":
			continue
		var say_text := _extract_say_text(item.get("actions", []))
		if say_text != "":
			_proactive_lines[npc_id] = say_text


func _extract_say_text(actions: Array) -> String:
	for action in actions:
		if typeof(action) == TYPE_DICTIONARY and action.get("action", "") == "say":
			return str(action.get("content", ""))
	return ""


func _close_dialogue_panel() -> void:
	_dialogue_panel.visible = false
	_dialogue_options = []
	var kept_active_npc := false
	for area in _npc_areas:
		var npc_data: Variant = area.get_meta("npc_data", {})
		if typeof(npc_data) == TYPE_DICTIONARY and _active_npc.get("id", "") == npc_data.get("id", ""):
			area.set_meta("proactive_state", "idle")
			_hold_npc_before_wandering(area)
			kept_active_npc = true
			break

	if kept_active_npc:
		_is_near_npc = true
		_hint_label.text = "按 Enter 和 %s 对话" % _active_npc.get("name", npc_display_name)
	else:
		_refresh_location_hint()


func _should_pause_npc(area: Area2D) -> bool:
	if _dialogue_panel.visible:
		return true

	var npc_data: Variant = area.get_meta("npc_data", {})
	if typeof(npc_data) != TYPE_DICTIONARY:
		return false

	if _is_near_npc and _active_npc.get("id", "") == npc_data.get("id", ""):
		return true

	return false


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_accept"):
		if _is_near_npc and not _dialogue_panel.visible:
			_open_dialogue()
			return
		if _dialogue_panel.visible:
			if _dialogue_options.is_empty() and not _active_npc.is_empty():
				_open_dialogue()
				return
			_submit_selected_dialogue_option()
			return

	if event.is_action_pressed("ui_down") and _dialogue_panel.visible:
		if _dialogue_options.size() > 0:
			_selected_option_index = min(_selected_option_index + 1, _dialogue_options.size() - 1)
			_render_dialogue_options()
		return

	if event.is_action_pressed("ui_up") and _dialogue_panel.visible:
		if _dialogue_options.size() > 0:
			_selected_option_index = max(_selected_option_index - 1, 0)
			_render_dialogue_options()
		return

	if event.is_action_pressed("ui_cancel") and _dialogue_panel.visible:
		_close_dialogue_panel()


func _update_hud() -> void:
	_time_label.text = "时间: %s" % _format_time(_minutes)
	_location_label.text = "地点: %s" % location_name
	_state_label.text = "状态: 精力100 心情70 压力20 专注60"


func _format_time(total_minutes: int) -> String:
	var hour := int(total_minutes / 60)
	var minute := int(total_minutes % 60)
	return "%02d:%02d" % [hour, minute]


func _on_npc_body_entered(body: Node, area: Area2D) -> void:
	if body != _player:
		return

	var npc_data: Variant = area.get_meta("npc_data", {})
	if typeof(npc_data) != TYPE_DICTIONARY:
		return

	_active_npc = npc_data
	_is_near_npc = true
	npc_display_name = str(_active_npc.get("name", npc_display_name))
	_stop_npc_at_current_position(area)
	_hint_label.text = "按 Enter 和 %s 对话" % npc_display_name


func _on_npc_body_exited(body: Node, area: Area2D) -> void:
	if body != _player:
		return

	_is_near_npc = false
	var npc_data: Variant = area.get_meta("npc_data", {})
	if typeof(npc_data) == TYPE_DICTIONARY and _active_npc.get("id", "") == npc_data.get("id", ""):
		_active_npc = {}

	_hold_npc_before_wandering(area)
	_refresh_location_hint()
	_dialogue_panel.visible = false


func _on_exit_body_entered(body: Node) -> void:
	if body != _player or _is_transitioning:
		return

	_is_transitioning = true
	_post_event(leave_event_type, location_name)
	_post_event(arrive_next_event_type, next_location_name)
	await get_tree().create_timer(0.1).timeout
	get_tree().change_scene_to_file(next_scene_path)


func _post_event(event_type: String, event_location: String) -> void:
	var payload := {
		"event_type": event_type,
		"location": event_location,
		"payload": {"source": "godot_client"},
		"game_time": _format_time(_minutes)
	}
	var body := JSON.stringify(payload)
	var headers := PackedStringArray(["Content-Type: application/json"])
	var err := _event_request.request(
		"%s/event" % backend_base_url,
		headers,
		HTTPClient.METHOD_POST,
		body
	)
	if err == OK:
		await _event_request.request_completed


func _sync_world_state() -> void:
	var err := _world_state_request.request("%s/world/state" % backend_base_url)
	if err != OK:
		return

	var result: Array = await _world_state_request.request_completed
	if result.size() != 4:
		return

	var raw_body: PackedByteArray = result[3]
	if raw_body == null:
		return

	var body_text: String = raw_body.get_string_from_utf8()
	var parsed: Variant = JSON.parse_string(body_text)
	if typeof(parsed) != TYPE_DICTIONARY:
		return

	if parsed.has("game_time"):
		_time_label.text = "时间: %s" % parsed["game_time"]
	if parsed.has("current_location"):
		_location_label.text = "地点: %s" % parsed["current_location"]
	if parsed.has("time_label"):
		_state_label.text = "状态: 当前阶段 %s" % parsed["time_label"]
	if parsed.has("player_state"):
		var state: Dictionary = parsed["player_state"]
		_state_label.text = "状态: 精力%s 心情%s 压力%s 专注%s 代码%s 学习%s 睡眠%s" % [
			state.get("energy", 100),
			state.get("mood", 70),
			state.get("stress", 20),
			state.get("focus", 60),
			state.get("code", 0),
			state.get("learning", 0),
			state.get("sleep_quality", 80)
		]
	if parsed.has("npcs"):
		_sync_npc_display(parsed["npcs"])


func _sync_npc_display(npcs: Array) -> void:
	var location_npcs: Array = []
	for npc_data in npcs:
		if typeof(npc_data) != TYPE_DICTIONARY:
			continue
		if npc_data.get("current_location", "") == location_name:
			location_npcs.append(npc_data)

	_ensure_npc_area_count(location_npcs.size())
	_is_near_npc = false
	_active_npc = {}
	_dialogue_panel.visible = false

	for i in range(_npc_areas.size()):
		var area := _npc_areas[i]
		var has_npc := i < location_npcs.size()
		area.visible = has_npc
		area.monitoring = has_npc
		_set_area_collision_enabled(area, has_npc)
		if not has_npc:
			area.set_meta("npc_data", {})
			area.set_meta("scene_presence", "present")
			area.set_meta("proactive_state", "idle")
			continue

		var npc_data: Dictionary = location_npcs[i]
		var previous_npc: Variant = area.get_meta("npc_data", {})
		var previous_id := ""
		if typeof(previous_npc) == TYPE_DICTIONARY:
			previous_id = str(previous_npc.get("id", ""))
		if previous_id != str(npc_data.get("id", "")):
			area.position = _layout_npc_position(i, location_npcs.size())
			area.set_meta("wander_state", _make_initial_wander_state(area.position))
			area.set_meta("scene_presence", "present")
			area.set_meta("proactive_state", "idle")
		area.set_meta("npc_data", npc_data)
		var npc_label = area.get_node_or_null("NpcLabel")
		if npc_label is Label:
			npc_label.text = str(npc_data.get("name", "NPC"))
		var presence := str(area.get_meta("scene_presence", "present"))
		var is_visible_in_scene := presence != "off_scene"
		area.visible = is_visible_in_scene
		area.monitoring = is_visible_in_scene
		_set_area_collision_enabled(area, is_visible_in_scene)

	_refresh_location_hint()


func _refresh_location_hint() -> void:
	var visible_npcs: Array[String] = []
	for area in _npc_areas:
		if not area.visible:
			continue
		var npc_data: Variant = area.get_meta("npc_data", {})
		if typeof(npc_data) == TYPE_DICTIONARY:
			visible_npcs.append("%s（%s）" % [
				npc_data.get("name", "NPC"),
				npc_data.get("current_action", "日常活动")
			])

	if visible_npcs.is_empty():
		_hint_label.text = "当前时间段此场景暂无 NPC"
	else:
		_hint_label.text = "场景 NPC：%s" % "、".join(visible_npcs)


func _open_dialogue() -> void:
	if _active_npc.is_empty():
		return

	_dialogue_panel.visible = true
	_dialogue_label.text = "%s：正在加载对话选项..." % _active_npc.get("name", npc_display_name)
	await _load_dialogue_options()


func _load_dialogue_options() -> void:
	var npc_id = str(_active_npc.get("id", ""))
	if npc_id == "":
		return

	var url := "%s/dialogue/options?npc_id=%s" % [backend_base_url, npc_id]
	var err := _dialogue_options_request.request(url)
	if err != OK:
		_dialogue_label.text = "对话选项加载失败"
		return

	var result: Array = await _dialogue_options_request.request_completed
	if result.size() != 4:
		_dialogue_label.text = "对话选项加载失败"
		return

	var raw_body: PackedByteArray = result[3]
	if raw_body == null:
		_dialogue_label.text = "对话选项加载失败"
		return

	var parsed: Variant = JSON.parse_string(raw_body.get_string_from_utf8())
	if typeof(parsed) != TYPE_DICTIONARY:
		_dialogue_label.text = "对话选项加载失败"
		return

	_dialogue_options = parsed.get("options", [])
	_selected_option_index = 0
	_render_dialogue_options()


func _render_dialogue_options() -> void:
	if _dialogue_options.is_empty():
		_dialogue_label.text = "当前没有可选对话。"
		return

	var title := "%s（%s）\n状态：%s\n目标：%s\n\n" % [
		_active_npc.get("name", npc_display_name),
		_active_npc.get("mood", "neutral"),
		_active_npc.get("current_action", "日常活动"),
		_active_npc.get("goal", "推进计划")
	]
	var lines: Array[String] = []
	for i in range(_dialogue_options.size()):
		var option: Dictionary = _dialogue_options[i]
		var prefix := "👉 " if i == _selected_option_index else "   "
		lines.append("%s%s" % [prefix, option.get("label", "未知选项")])

	_dialogue_label.text = title + "\n".join(lines)


func _submit_selected_dialogue_option() -> void:
	if _dialogue_options.is_empty():
		return
	var selected: Dictionary = _dialogue_options[_selected_option_index]
	var npc_id = str(_active_npc.get("id", ""))
	if npc_id == "":
		return

	var payload := {
		"npc_id": npc_id,
		"option_id": selected.get("id", "end_chat"),
		"use_llm": false
	}
	var body := JSON.stringify(payload)
	var headers := PackedStringArray(["Content-Type: application/json"])
	var err := _dialogue_choice_request.request(
		"%s/dialogue/choice" % backend_base_url,
		headers,
		HTTPClient.METHOD_POST,
		body
	)
	if err != OK:
		_dialogue_label.text = "对话提交失败"
		return

	var result: Array = await _dialogue_choice_request.request_completed
	if result.size() != 4:
		_dialogue_label.text = "对话提交失败"
		return

	var raw_body: PackedByteArray = result[3]
	if raw_body == null:
		_dialogue_label.text = "对话提交失败"
		return

	var parsed: Variant = JSON.parse_string(raw_body.get_string_from_utf8())
	if typeof(parsed) != TYPE_DICTIONARY:
		_dialogue_label.text = "对话提交失败"
		return

	var reply_text: String = parsed.get("reply", "...")
	_dialogue_label.text = "%s：%s\n\n按 Esc 关闭，按 Enter 继续选择。" % [
		_active_npc.get("name", npc_display_name),
		reply_text
	]
	await _sync_world_state()
	await _load_dialogue_options()


func _post_player_action(action_type: String, event_location: String) -> void:
	var payload := {
		"action_type": action_type,
		"location": event_location,
		"payload": {
			"source": "godot_client",
			"description": "%s 执行 %s" % [event_location, action_type]
		},
		"game_time": _format_time(_minutes)
	}
	var body := JSON.stringify(payload)
	var headers := PackedStringArray(["Content-Type: application/json"])
	var err := _player_action_request.request(
		"%s/player/action" % backend_base_url,
		headers,
		HTTPClient.METHOD_POST,
		body
	)
	if err == OK:
		await _player_action_request.request_completed


func _generate_daily_review() -> void:
	_dialogue_panel.visible = true
	_dialogue_label.text = "正在生成今日复盘..."
	var headers := PackedStringArray(["Content-Type: application/json"])
	var err := _daily_review_request.request(
		"%s/daily/review" % backend_base_url,
		headers,
		HTTPClient.METHOD_POST,
		"{}"
	)
	if err != OK:
		_dialogue_label.text = "今日复盘生成失败"
		return

	var result: Array = await _daily_review_request.request_completed
	if result.size() != 4:
		_dialogue_label.text = "今日复盘生成失败"
		return

	var raw_body: PackedByteArray = result[3]
	if raw_body == null:
		_dialogue_label.text = "今日复盘生成失败"
		return

	var parsed: Variant = JSON.parse_string(raw_body.get_string_from_utf8())
	if typeof(parsed) != TYPE_DICTIONARY:
		_dialogue_label.text = "今日复盘生成失败"
		return

	var route_text := " → ".join(parsed.get("route", []))
	var keywords_text := "、".join(parsed.get("keywords", []))
	_dialogue_label.text = "今日复盘\n路线：%s\n关键词：%s\n\n%s\n\n明天：%s\n\n按 Esc 关闭。" % [
		route_text,
		keywords_text,
		parsed.get("summary", "今天完整走完了一天。"),
		parsed.get("tomorrow_hint", "明天继续保持节奏。")
	]


func _load_proactive_action() -> void:
	var url := "%s/npc/proactive?location=%s&limit=1" % [backend_base_url, location_name.uri_encode()]
	var err := _proactive_request.request(url)
	if err != OK:
		return

	var result: Array = await _proactive_request.request_completed
	if result.size() != 4:
		return

	var raw_body: PackedByteArray = result[3]
	if raw_body == null:
		return

	var parsed: Variant = JSON.parse_string(raw_body.get_string_from_utf8())
	if typeof(parsed) != TYPE_DICTIONARY:
		return

	var items: Array = parsed.get("proactive_actions", [])
	if items.is_empty():
		return

	var item: Dictionary = items[0]
	var actions: Array = item.get("actions", [])
	var say_text := ""
	for action in actions:
		if typeof(action) == TYPE_DICTIONARY and action.get("action", "") == "say":
			say_text = str(action.get("content", ""))
			break
	if say_text == "":
		return

	_dialogue_panel.visible = true
	_dialogue_label.text = "%s：%s\n\n按 Esc 关闭。" % [
		item.get("npc_name", "NPC"),
		say_text
	]
