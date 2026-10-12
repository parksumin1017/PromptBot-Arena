"""Core Pusher Game Referee & Match Rule Engine for PromptBot Arena.

Strictly follows specifications from docs/design.md & docs/overview.md:
- Match time: 60.0 seconds limit
- Midline: x = 300.0 mm
- Red Zone: x < 300.0 mm
- Blue Zone: x >= 300.0 mm
- Core Pusher Scoring:
    - Red Score = Number of pucks pushed into Blue Zone (x >= 300.0 mm)
    - Blue Score = Number of pucks pushed into Red Zone (x < 300.0 mm)
- Winner:
    - Team with more pucks pushed into opponent zone wins.
    - Equal scores result in a DRAW.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional
from src.core.models import Puck


class MatchStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"


class MatchWinner(str, Enum):
    NONE = "none"
    RED = "red"
    BLUE = "blue"
    DRAW = "draw"


@dataclass(frozen=True)
class MatchScore:
    """Current match score breakdown."""
    red_score: int         # Pucks in Blue zone (x >= 300.0)
    blue_score: int        # Pucks in Red zone (x < 300.0)
    pucks_in_red: int      # Count of pucks in Red zone
    pucks_in_blue: int     # Count of pucks in Blue zone


@dataclass(frozen=True)
class MatchResult:
    """Official match status and result report."""
    status: MatchStatus
    winner: MatchWinner
    match_time: float
    time_remaining: float
    score: MatchScore
    message: str


class CorePusherReferee:
    """
    Official automated referee for Core Pusher matches.
    Evaluates puck zones, tracks remaining time, and decides official outcome.
    """

    MIDLINE_X: float = 300.0
    MAX_MATCH_TIME: float = 60.0

    def __init__(self, max_match_time: float = 60.0):
        self.max_match_time = max_match_time

    def evaluate_zones(self, pucks: List[Puck]) -> Tuple[int, int]:
        """
        Count pucks in (Red Zone, Blue Zone).
        - Red Zone: x < 300.0 mm
        - Blue Zone: x >= 300.0 mm
        """
        pucks_in_red = sum(1 for p in pucks if p.x < self.MIDLINE_X)
        pucks_in_blue = sum(1 for p in pucks if p.x >= self.MIDLINE_X)
        return pucks_in_red, pucks_in_blue

    def calculate_score(self, pucks: List[Puck]) -> MatchScore:
        """
        Calculate score for Core Pusher:
        - Red Score = pucks pushed into Blue Zone
        - Blue Score = pucks pushed into Red Zone
        """
        pucks_in_red, pucks_in_blue = self.evaluate_zones(pucks)
        # Red scores by having pucks in Blue zone, Blue scores by having pucks in Red zone
        red_score = pucks_in_blue
        blue_score = pucks_in_red
        return MatchScore(
            red_score=red_score,
            blue_score=blue_score,
            pucks_in_red=pucks_in_red,
            pucks_in_blue=pucks_in_blue
        )

    def determine_winner(self, score: MatchScore) -> MatchWinner:
        """Determine winner based on puck count in opponent territory."""
        if score.red_score > score.blue_score:
            return MatchWinner.RED
        elif score.blue_score > score.red_score:
            return MatchWinner.BLUE
        else:
            return MatchWinner.DRAW

    def update(self, match_time: float, pucks: List[Puck]) -> MatchResult:
        """
        Evaluate match state at given match_time and puck positions.
        """
        score = self.calculate_score(pucks)
        time_rem = max(0.0, self.max_match_time - match_time)

        if match_time <= 0.0:
            status = MatchStatus.NOT_STARTED
            winner = MatchWinner.NONE
            message = "Match has not started."
        elif match_time >= self.max_match_time:
            status = MatchStatus.FINISHED
            winner = self.determine_winner(score)
            if winner == MatchWinner.RED:
                message = f"MATCH FINISHED - RED WINS ({score.red_score} : {score.blue_score})!"
            elif winner == MatchWinner.BLUE:
                message = f"MATCH FINISHED - BLUE WINS ({score.blue_score} : {score.red_score})!"
            else:
                message = f"MATCH FINISHED - DRAW ({score.red_score} : {score.blue_score})!"
        else:
            status = MatchStatus.IN_PROGRESS
            winner = MatchWinner.NONE
            message = f"MATCH IN PROGRESS ({score.red_score} : {score.blue_score})"

        return MatchResult(
            status=status,
            winner=winner,
            match_time=match_time,
            time_remaining=time_rem,
            score=score,
            message=message
        )
