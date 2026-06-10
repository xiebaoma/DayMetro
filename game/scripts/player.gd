extends CharacterBody2D

@export var speed := 180.0

func _ready() -> void:
	var visual := ColorRect.new()
	visual.name = "PlayerVisual"
	visual.size = Vector2(28, 28)
	visual.color = Color(0.3, 0.7, 1.0, 1)
	visual.position = Vector2(-14, -14)
	add_child(visual)

	var label := Label.new()
	label.name = "PlayerLabel"
	label.text = "我"
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	label.size = Vector2(28, 28)
	label.position = Vector2(-14, -14)
	add_child(label)

func _physics_process(_delta: float) -> void:
	var move_vector := Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")
	velocity = move_vector * speed
	move_and_slide()
