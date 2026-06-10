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
var _dialogue_options: Array = []
var _selected_option_index := 0

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

	# NPC visual marker
	var npc_marker := ColorRect.new()
	npc_marker.name = "NpcMarker"
	npc_marker.size = Vector2(32, 48)
	npc_marker.color = Color(1.0, 0.84, 0.0, 0.5)
	npc_marker.position = Vector2(-16, -38)
	_npc_area.add_child(npc_marker)

	var npc_label := Label.new()
	npc_label.name = "NpcLabel"
	npc_label.text = "NPC"
	npc_label.add_theme_font_size_override("font_size", 10)
	npc_label.add_theme_color_override("font_color", Color.WHITE)
	npc_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	npc_label.size = Vector2(32, 14)
	npc_label.position = Vector2(-16, 14)
	_npc_area.add_child(npc_label)

	# Exit visual marker
	var exit_marker := ColorRect.new()
	exit_marker.name = "ExitMarker"
	exit_marker.size = Vector2(48, 120)
	exit_marker.color = Color(0.2, 1.0, 0.2, 0.3)
	exit_marker.position = Vector2(-24, -60)
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
	_npc_area.body_entered.connect(_on_npc_body_entered)
	_npc_area.body_exited.connect(_on_npc_body_exited)
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
		await _load_proactive_action()


func _process(delta: float) -> void:
	_tick_accumulator += delta
	if _tick_accumulator >= 1.0:
		_tick_accumulator = 0.0
		_minutes = min(_minutes + 5, 23 * 60 + 59)
		_update_hud()


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_accept"):
		if _is_near_npc and not _dialogue_panel.visible:
			_open_dialogue()
			return
		if _dialogue_panel.visible:
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
		_dialogue_panel.visible = false


func _update_hud() -> void:
	_time_label.text = "时间: %s" % _format_time(_minutes)
	_location_label.text = "地点: %s" % location_name
	_state_label.text = "状态: 精力100 心情70 压力20 专注60"


func _format_time(total_minutes: int) -> String:
	var hour := int(total_minutes / 60)
	var minute := int(total_minutes % 60)
	return "%02d:%02d" % [hour, minute]


func _on_npc_body_entered(body: Node) -> void:
	if body == _player and not _active_npc.is_empty():
		_is_near_npc = true
		_hint_label.text = "按 Enter 和 %s 对话" % _active_npc.get("name", npc_display_name)


func _on_npc_body_exited(body: Node) -> void:
	if body == _player:
		_is_near_npc = false
		if not _active_npc.is_empty():
			_hint_label.text = "场景 NPC：%s（%s）" % [
				_active_npc.get("name", npc_display_name),
				_active_npc.get("current_action", "日常活动")
			]
		else:
			_hint_label.text = "当前时间段此场景暂无 NPC"
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
	_active_npc = {}
	for npc_data in npcs:
		if typeof(npc_data) != TYPE_DICTIONARY:
			continue
		if npc_data.get("current_location", "") == location_name:
			_active_npc = npc_data
			break

	var has_npc := not _active_npc.is_empty()
	_npc_area.visible = has_npc
	_npc_area.monitoring = has_npc
	_npc_collision.disabled = not has_npc
	_is_near_npc = false
	_dialogue_panel.visible = false

	if has_npc:
		npc_display_name = str(_active_npc.get("name", npc_display_name))
		_hint_label.text = "场景 NPC：%s（%s）" % [
			_active_npc.get("name", npc_display_name),
			_active_npc.get("current_action", "日常活动")
		]
	else:
		_hint_label.text = "当前时间段此场景暂无 NPC"


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
