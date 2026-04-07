from snake_game import GameState


def test_snake_moves_forward():
    state = GameState()

    state.step()

    assert state.snake == [(6, 10), (5, 10), (4, 10)]
    assert state.score == 0
    assert not state.game_over


def test_snake_grows_after_eating_food():
    state = GameState(food=(6, 10))

    state.step()

    assert state.snake == [(6, 10), (5, 10), (4, 10), (3, 10)]
    assert state.score == 1
    assert state.food not in state.snake


def test_snake_cannot_reverse_direction():
    state = GameState(direction="Right")

    state.change_direction("Left")

    assert state.direction == "Right"


def test_wall_collision_ends_the_game():
    state = GameState(
        width=5,
        height=5,
        snake=[(4, 2), (3, 2), (2, 2)],
        direction="Right",
        food=(0, 0),
    )

    state.step()

    assert state.game_over


def test_body_collision_ends_the_game():
    state = GameState(
        snake=[(5, 5), (4, 5), (4, 6), (5, 6), (6, 6), (6, 5)],
        direction="Left",
        food=(0, 0),
    )

    state.change_direction("Down")
    state.step()

    assert state.game_over
