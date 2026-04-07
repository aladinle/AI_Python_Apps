import random
import tkinter as tk
from dataclasses import dataclass, field


BOARD_WIDTH = 20
BOARD_HEIGHT = 20
CELL_SIZE = 24
DEFAULT_TICK_MS = 140


@dataclass
class GameState:
    width: int = BOARD_WIDTH
    height: int = BOARD_HEIGHT
    direction: str = "Right"
    score: int = 0
    game_over: bool = False
    snake: list[tuple[int, int]] = field(
        default_factory=lambda: [(5, 10), (4, 10), (3, 10)]
    )
    food: tuple[int, int] = (10, 10)

    def __post_init__(self) -> None:
        if self.food in self.snake:
            self.food = self._spawn_food()

    def change_direction(self, next_direction: str) -> None:
        opposites = {
            "Up": "Down",
            "Down": "Up",
            "Left": "Right",
            "Right": "Left",
        }
        if next_direction != opposites[self.direction]:
            self.direction = next_direction

    def step(self) -> None:
        if self.game_over:
            return

        head_x, head_y = self.snake[0]
        delta_x, delta_y = {
            "Up": (0, -1),
            "Down": (0, 1),
            "Left": (-1, 0),
            "Right": (1, 0),
        }[self.direction]
        new_head = (head_x + delta_x, head_y + delta_y)

        if self._hits_wall(new_head):
            self.game_over = True
            return

        growing = new_head == self.food
        body_to_check = self.snake if growing else self.snake[:-1]
        if new_head in body_to_check:
            self.game_over = True
            return

        self.snake.insert(0, new_head)
        if growing:
            self.score += 1
            if len(self.snake) == self.width * self.height:
                self.game_over = True
                return
            self.food = self._spawn_food()
        else:
            self.snake.pop()

    def _hits_wall(self, position: tuple[int, int]) -> bool:
        x, y = position
        return x < 0 or y < 0 or x >= self.width or y >= self.height

    def _spawn_food(self) -> tuple[int, int]:
        free_spaces = [
            (x, y)
            for y in range(self.height)
            for x in range(self.width)
            if (x, y) not in self.snake
        ]
        return random.choice(free_spaces)


class SnakeApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Snake")
        self.root.resizable(False, False)

        self.state = GameState()
        self.running = False

        self.score_var = tk.StringVar(value="Score: 0")
        self.status_var = tk.StringVar(value="Press Space to start")

        info_frame = tk.Frame(self.root, padx=12, pady=8)
        info_frame.pack(fill="x")

        tk.Label(
            info_frame,
            textvariable=self.score_var,
            font=("Helvetica", 14, "bold"),
        ).pack(side="left")
        tk.Label(
            info_frame,
            textvariable=self.status_var,
            font=("Helvetica", 11),
        ).pack(side="right")

        self.canvas = tk.Canvas(
            self.root,
            width=self.state.width * CELL_SIZE,
            height=self.state.height * CELL_SIZE,
            bg="#111111",
            highlightthickness=0,
        )
        self.canvas.pack(padx=12, pady=(0, 12))

        self.root.bind("<Up>", lambda _: self.state.change_direction("Up"))
        self.root.bind("<Down>", lambda _: self.state.change_direction("Down"))
        self.root.bind("<Left>", lambda _: self.state.change_direction("Left"))
        self.root.bind("<Right>", lambda _: self.state.change_direction("Right"))
        self.root.bind("<space>", lambda _: self.toggle_running())
        self.root.bind("r", lambda _: self.reset())
        self.root.bind("R", lambda _: self.reset())

        self.draw()

    def toggle_running(self) -> None:
        if self.state.game_over:
            self.reset()
            return

        self.running = not self.running
        self.status_var.set("Running" if self.running else "Paused")
        if self.running:
            self._tick()

    def reset(self) -> None:
        self.state = GameState()
        self.running = False
        self.score_var.set("Score: 0")
        self.status_var.set("Press Space to start")
        self.draw()

    def _tick(self) -> None:
        if not self.running:
            return

        self.state.step()
        self.score_var.set(f"Score: {self.state.score}")
        if self.state.game_over:
            self.running = False
            self.status_var.set("Game over - press R to restart")
        self.draw()

        if self.running:
            self.root.after(DEFAULT_TICK_MS, self._tick)

    def draw(self) -> None:
        self.canvas.delete("all")
        self._draw_grid()
        self._draw_food()
        self._draw_snake()
        if self.state.game_over:
            self._draw_overlay("Game Over", "Press R to restart")

    def _draw_grid(self) -> None:
        for x in range(self.state.width):
            for y in range(self.state.height):
                x1 = x * CELL_SIZE
                y1 = y * CELL_SIZE
                x2 = x1 + CELL_SIZE
                y2 = y1 + CELL_SIZE
                self.canvas.create_rectangle(
                    x1,
                    y1,
                    x2,
                    y2,
                    outline="#1f1f1f",
                    fill="#161616",
                )

    def _draw_food(self) -> None:
        x, y = self.state.food
        padding = 4
        x1 = x * CELL_SIZE + padding
        y1 = y * CELL_SIZE + padding
        x2 = x1 + CELL_SIZE - (padding * 2)
        y2 = y1 + CELL_SIZE - (padding * 2)
        self.canvas.create_oval(x1, y1, x2, y2, fill="#ff5c5c", outline="")

    def _draw_snake(self) -> None:
        for index, (x, y) in enumerate(self.state.snake):
            padding = 2
            x1 = x * CELL_SIZE + padding
            y1 = y * CELL_SIZE + padding
            x2 = x1 + CELL_SIZE - (padding * 2)
            y2 = y1 + CELL_SIZE - (padding * 2)
            color = "#6cff6c" if index == 0 else "#2ecc71"
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")

    def _draw_overlay(self, title: str, subtitle: str) -> None:
        width = self.state.width * CELL_SIZE
        height = self.state.height * CELL_SIZE
        self.canvas.create_rectangle(0, 0, width, height, fill="#000000", stipple="gray50")
        self.canvas.create_text(
            width / 2,
            height / 2 - 16,
            text=title,
            fill="#ffffff",
            font=("Helvetica", 22, "bold"),
        )
        self.canvas.create_text(
            width / 2,
            height / 2 + 16,
            text=subtitle,
            fill="#ffffff",
            font=("Helvetica", 12),
        )

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    SnakeApp().run()
