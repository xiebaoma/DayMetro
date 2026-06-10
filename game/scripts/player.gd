extends CharacterBody2D

@export var speed := 180.0

func _physics_process(_delta: float) -> void:
    var move_vector := Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")
    velocity = move_vector * speed
    move_and_slide()
