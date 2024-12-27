import pyxel
import json

from enum import Enum, auto
from math import radians, sin, cos
from dataclasses import dataclass

from ball import Ball
from paddle import Paddle 
from brick import Brick


class GameState(Enum):
    """ Game states enumeration """
    READY = auto() # ready to start 
    RUNNING = auto() # in progress
    DROPPED = auto() # ball is out of bounds 
    GAME_OVER = auto() # player lost the game
    WIN = auto() # player won the game

@dataclass
class GameStats:
    score: int = 0 # score tracker
    lives: int = 0 # lives tracker

class BreakoutGame:
    def __init__(self) -> None:
        """ Constructor """

        self._init_pyxel() # initializes pyxel settings
        self.gravity: float = 0.007
        self.stats: GameStats # holds game stats
         
        self.paddle: Paddle = Paddle() # initializes a paddle
        # relates to the indicator when game starts
        self.angle: float # angle tracker for indicator
        self.angle_direction: float # 1 is left to right, -1 is right to left
        self.angle_cycle_speed: float # degrees per frame     

        self.ball: Ball = Ball(self.gravity) # initializes a ball 
        self._reset_ball() # makes sure that ball starts at paddle 

        self.stages: list[dict[str, list[dict[str, int]]]] = self._load_stages("../assets/stages.json") # contains all the predefined stages
        self.current_stage: int # tracks the current stage no. 
        self.bricks: list[Brick] = [] # tracks the list of bricks imported from the current stage

        self.current_game_state: GameState = GameState.READY # game state tracker
        self._start_new_game() # starts a new game

        pyxel.run(self._update, self._draw) # runs game loop

    @classmethod
    def _init_pyxel(cls) -> None:
        """ Initializes Pyxel engine settings """
        pyxel.init(width=450, height=200, display_scale=3, title="Breakout Game", fps=60)
        pyxel.load("../assets/resources.pyxres") # our resource file

    # +++++++++++++++++++++++++++++++++ STAGE MANAGEMENT +++++++++++++++++++++++++++++++++

    @classmethod
    def _load_stages(cls, file_path: str) -> list[dict[str, list[dict[str, int]]]]:
        """ Load stages from JSON file."""
        with open(file_path, "r") as f:
            data = json.load(f)
        return data["stages"]

    def _load_stage(self, stage_index: int) -> None:
        """ Load a specific stage."""
        stage = self.stages[stage_index] # stages is 0-indexed
        self.bricks = [
            Brick(brick["x"], brick["y"], brick["brick_type"])
            for brick in stage["bricks"]
        ]

    def _next_stage(self) -> None:
        """ Move to the next stage."""
        if self.current_stage < len(self.stages):
            self.current_stage += 1
            self._load_stage(self.current_stage - 1) # stages is 0-indexed
            self._reset_ball()
            self.current_game_state = GameState.READY
        else:
            self.current_game_state = GameState.WIN

# +++++++++++++++++++++++++++++++++ HELPER METHODS +++++++++++++++++++++++++++++++++

    def _start_new_game(self) -> None:
        """ Starts a new game """
        self.stats = GameStats() # initializes a GameStats object for new game
        self.current_stage = 1 # sets the current stage to the first one (1-indexed)
        self._load_stage(self.current_stage - 1) # loads the current stage
        self._reset_ball() # resets ball position to paddle
        self.current_game_state = GameState.READY # sets the gamestate to the READY state
        
    def _reset_ball(self):
        """ Resets the ball to paddle """
        self.ball.clear_trails() # removes trails that could still be up
        self.ball.y = self.paddle.y - self.ball.r * 2    # Keeps the ball above the paddle
        self.angle = 0 # indicator starts with 0 deg
        self.angle_direction = 1 # start going left to right
        self.angle_cycle_speed = 2 # 2 degrees per frame
        # ball is not launched yet
        self.ball.speed_x = 0 
        self.ball.speed_y = 0
        # resets ball's out of bounds state
        self.ball.out_of_bounds = False

    def _launch_ball(self):
        """ Launches the ball based on the current angle """
        angle_rad: float = radians(self.angle)
        self.ball.speed_x = cos(angle_rad) * 2.5
        self.ball.speed_y = -sin(angle_rad) * 2.5

        # transitions to running state
        self.current_game_state = GameState.RUNNING

    def _check_collision(self) -> None:
        """ Checks for all kinds of collisions """
        # Ball vs Paddle
        collision: bool = self.ball.detect_collision(self.paddle, is_paddle=True)
        
        # Ball vs Bricks
        for i in reversed(range(len(self.bricks))): # checks all bricks for collisions
            b: Brick = self.bricks[i]
            collision = self.ball.detect_collision(b)
            if collision:
                del self.bricks[i] # removes brick that collides with ball (for now)
                break

    def _check_input(self) -> None:
        """ Checks for inputs by user (depending on the game state)"""
        if self.current_game_state == GameState.READY:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT) or pyxel.btnp(pyxel.KEY_SPACE):
                self._launch_ball() # launches the ball
    
        if self.current_game_state in {GameState.GAME_OVER, GameState.WIN}:
            if pyxel.btnp(pyxel.KEY_RETURN): # press enter to start a new game
                self._start_new_game()

# +++++++++++++++++++++++++++++++++ UPDATE METHODS +++++++++++++++++++++++++++++++++

    def _update_ready_state(self) -> None:
        """ Update logic for READY state """
        self.ball.x = self.paddle.x + self.paddle.w / 2 - self.ball.r # centers the ball at the paddle's horizontal center

        # Oscillate the angle left to right, then right to left
        self.angle += self.angle_direction * self.angle_cycle_speed

        # Reverse direction at bounds
        if self.angle == 180 or self.angle == 0:
            self.angle_direction = -self.angle_direction # reversed direction
    
    def _update_running_state(self) -> None:
        """ Update logic for RUNNING state """
        self.ball.update() # moves the ball
        self._check_collision() # checks for collisions

        if not self.bricks: # all bricks cleared (stage cleared)
            if self.current_stage == len(self.stages): # last stage cleared
                self.current_game_state = GameState.WIN
            else:
                self._next_stage()

        if self.ball.out_of_bounds: # if ball dropped
            self.current_game_state = GameState.DROPPED
    
    def _update_dropped_state(self) -> None:
        """ Update logic for DROPPED state """
        self.stats.lives -= 1
        if self.stats.lives > 0: # if player still has lives
            self._reset_ball()
            self.current_game_state = GameState.READY
        else:
            self.current_game_state = GameState.GAME_OVER
    
    def _update(self) -> None:
        """ General update method """
        self._check_input()
        self.paddle.update()

        match self.current_game_state:
            case GameState.READY:
                self._update_ready_state()
            case GameState.RUNNING:
                self._update_running_state()
            case GameState.DROPPED:
                self._update_dropped_state()
            case GameState.GAME_OVER:
                pass # to be added
            case GameState.WIN:
                pass # to be added 

# +++++++++++++++++++++++++++++++++ DRAW METHODS +++++++++++++++++++++++++++++++++

    def _draw_ready_state(self) -> None:
        """ Draws elements for READY state """

        self._draw_game_elements()  # draws the paddle, ball, and bricks
        self._draw_ui() # draws the ui

        angle_rad = radians(self.angle) # angle from degrees to radians
        indicator_length = 25  # length of the indicator line
        x_end = self.paddle.x + self.paddle.w / 2 + indicator_length * cos(angle_rad) # the x-coord of the end of the indicator line
        y_end = self.paddle.y - indicator_length * sin(angle_rad) # the y-coord of the end of the indicator line

        # draws the indicator line
        pyxel.line(
            self.paddle.x + self.paddle.w / 2,
            self.paddle.y,
            x_end,
            y_end,
            pyxel.COLOR_RED
        )

        # adds blinking text instruction
        if (pyxel.frame_count // 30) % 2 == 0:  # toggle every 30 frames
            pyxel.text(
                pyxel.width // 2 - 50,  # centered horizontally
                pyxel.height // 2,  # centered vertically
                "Left Mouse Click to Launch!",
                pyxel.COLOR_BLACK,
                None
            )
        
    def _draw_running_state(self) -> None:
        """ Draws the RUNNING state """
        self._draw_game_elements()  # draws the paddle, ball, and bricks
        self._draw_ui() # draws the ui

    def _draw_game_over_state(self) -> None:
        """ Draws the GAME_OVER state """
        # draws game over text
        
        pyxel.blt(x=139, y=80, img=0, u=48, v=32, w=176, h=16, colkey=pyxel.COLOR_WHITE, scale=2)
        pyxel.text(x=175, y=130, s="Press Enter to Play Again!", col=pyxel.COLOR_BLACK, font=None)
    
    def _draw_game_elements(self) -> None:
        """ Draws the paddle, ball, and bricks """
        self.paddle.draw()
        for brick in self.bricks:
            brick.draw()
        self.ball.draw()
    
    def _draw_ui(self) -> None:
        """ Draw UI elements like score and lives """
        heart_x: float = 10  # starting x position for hearts
        heart_y: float = 10  # starting y position for hearts (top-left corner)
        heart_spacing: float = 9  # spacing between each heart (adjusted for 16x16 hearts)
        row_limit: int = 10  # max hearts per row

        # Draw hearts for lives
        for i in range(self.stats.lives):
            x = heart_x + (i % row_limit) * heart_spacing  # horizontal position
            y = heart_y + (i // row_limit) * heart_spacing  # vertical position
            pyxel.blt(
                x,  # x position of each heart
                y,  # y position
                0,  # bank
                0,  # u (x coordinate in the asset)
                0,  # v (y coordinate in the asset)
                16,  # width of the heart
                16,  # height of the heart
                pyxel.COLOR_ORANGE,  # transparency color
                scale=0.5 # scaled down
            )
        pyxel.text(10, pyxel.height - 20, f"Score: {self.stats.score}", pyxel.COLOR_BLACK, None)


    def _draw(self) -> None:
        """ General drawing method """

        pyxel.cls(pyxel.COLOR_LIGHT_BLUE)

        match self.current_game_state:
            case GameState.READY:
                self._draw_ready_state()
            case GameState.RUNNING:
                self._draw_running_state()
            case GameState.DROPPED:
                # some indicator that the ball dropped (visual effect only)
                pass # to be added (maybe?)
            case GameState.GAME_OVER:
                self._draw_game_over_state()

            case GameState.WIN:
                pyxel.text(10, pyxel.height - 10, "Game Over! You've completed all stages!", pyxel.COLOR_WHITE, None)
        
        
BreakoutGame() # game call
