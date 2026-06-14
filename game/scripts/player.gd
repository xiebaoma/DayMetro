extends CharacterBody2D

@export var speed := 180.0

func _ready() -> void:
	_build_player_sprite()

	var label := Label.new()
	label.name = "PlayerLabel"
	label.text = "我"
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	label.add_theme_font_size_override("font_size", 12)
	label.add_theme_color_override("font_color", Color(0.95, 0.98, 1.0, 1))
	label.size = Vector2(36, 18)
	label.position = Vector2(-18, -62)
	add_child(label)

func _physics_process(_delta: float) -> void:
	var move_vector := Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")
	velocity = move_vector * speed
	move_and_slide()


func _build_player_sprite() -> void:
	var shadow := Polygon2D.new()
	shadow.name = "Shadow"
	shadow.polygon = _ellipse_points(Vector2(0, 18), 18, 6)
	shadow.color = Color(0.02, 0.025, 0.03, 0.28)
	add_child(shadow)

	var legs := Polygon2D.new()
	legs.name = "Legs"
	legs.polygon = PackedVector2Array([
		Vector2(-9, 7), Vector2(-1, 7), Vector2(-3, 24), Vector2(-12, 24),
		Vector2(1, 7), Vector2(9, 7), Vector2(12, 24), Vector2(3, 24)
	])
	legs.color = Color(0.13, 0.19, 0.27, 1)
	add_child(legs)

	var body := Polygon2D.new()
	body.name = "Body"
	body.polygon = PackedVector2Array([
		Vector2(-15, -22), Vector2(15, -22), Vector2(20, 9), Vector2(-20, 9)
	])
	body.color = Color(0.14, 0.48, 0.82, 1)
	add_child(body)

	var shirt_highlight := Polygon2D.new()
	shirt_highlight.name = "ShirtHighlight"
	shirt_highlight.polygon = PackedVector2Array([
		Vector2(-11, -18), Vector2(7, -18), Vector2(11, 5), Vector2(-15, 5)
	])
	shirt_highlight.color = Color(0.33, 0.69, 0.96, 0.8)
	add_child(shirt_highlight)

	var head := Polygon2D.new()
	head.name = "Head"
	head.polygon = _ellipse_points(Vector2(0, -35), 13, 14)
	head.color = Color(0.96, 0.74, 0.55, 1)
	add_child(head)

	var hair := Polygon2D.new()
	hair.name = "Hair"
	hair.polygon = PackedVector2Array([
		Vector2(-13, -40), Vector2(-7, -50), Vector2(5, -51), Vector2(14, -42),
		Vector2(10, -35), Vector2(-12, -34)
	])
	hair.color = Color(0.08, 0.07, 0.06, 1)
	add_child(hair)


func _ellipse_points(center: Vector2, radius_x: float, radius_y: float) -> PackedVector2Array:
	var points := PackedVector2Array()
	for i in range(24):
		var angle := TAU * float(i) / 24.0
		points.append(center + Vector2(cos(angle) * radius_x, sin(angle) * radius_y))
	return points
