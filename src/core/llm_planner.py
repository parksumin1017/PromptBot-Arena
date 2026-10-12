"""Code-as-Policies (CaP) LLM Planner for PromptBot Arena.

Translates human natural language strategy instructions into executable,
AST-validated Python policy functions: def policy_step(state: State) -> ActionCommand.
"""

import re
import time
from typing import Tuple, Optional
from src.core.interfaces import CodePolicyAgent
from src.core.security import validate_policy_ast
from src.core.llm_clients import BaseLLMClient, create_llm_client


SYSTEM_PROMPT = """You are an expert autonomous robot tactics engineer for PromptBot Arena.
Your task is to write a single Python function:
def policy_step(state: State) -> ActionCommand:
that implements the user's high-level strategy for the Core Pusher match.

[Game Context & Geometry]
- Arena: 600 mm (width) x 400 mm (height). Coordinates: (0, 0) top-left to (600, 400) bottom-right.
- Midline: x = 300.0 mm.
- Red Zone: x < 300.0 mm. Blue Zone: x >= 300.0 mm.
- Match goal: Push 3 pucks into the opponent's territory.
  - If state.my_team == 'red', push target is deep into Blue zone: e.g. (450.0, 200.0).
  - If state.my_team == 'blue', push target is deep into Red zone: e.g. (150.0, 200.0).

[State Observation DTO]
- state.my_pos: (x, y) tuple [mm]
- state.my_theta: heading angle [rad]
- state.my_team: 'red' or 'blue'
- state.opp_pos: (x, y) tuple [mm]
- state.pucks: list of Puck objects (each has p.id, p.x, p.y, p.pos, p.zone)
- state.match_time: elapsed match time in seconds (0.0 to 60.0)

[Available Action Primitives API]
1. push(puck: Puck, target: Tuple[float, float]) -> ActionCommand
   Pushes the selected puck toward target coordinate using smooth trajectory profile.
2. move_to(target: Tuple[float, float]) -> ActionCommand
   Drives the robot smoothly to the target coordinate without touching pucks.
3. stop() -> ActionCommand
   Immediately stops all motor velocities.
4. will_collide(action: ActionCommand) -> bool
   Returns True if the action has imminent collision risk with opponent robot or obstacles.
5. get_closest_puck(pucks: List[Puck], to_pos: Tuple[float, float]) -> Optional[Puck]
   Returns the nearest Puck from to_pos.
6. get_pucks_in_zone(pucks: List[Puck], zone: str) -> List[Puck]
   Returns list of pucks located in zone ('red' or 'blue').
7. get_dist(pos1: Tuple[float, float], pos2: Tuple[float, float]) -> float
   Returns Euclidean distance in mm between two coordinates.

[Strict Output Format]
You MUST respond with a JSON object containing a single key "code":
{
  "code": "def policy_step(state: State) -> ActionCommand:\\n    ..."
}
Do NOT import any modules. All necessary Primitives (push, move_to, stop, will_collide, get_closest_puck, get_pucks_in_zone, get_dist) are already in scope.
Do NOT use while loops, eval, exec, open, or dunder (__) attributes.
"""


class LLMPlanner:
    """
    High-level CaP planner that invokes LLM and verifies AST compliance.
    """

    def __init__(self, client: Optional[BaseLLMClient] = None):
        self.client = client or create_llm_client()

    def generate_policy_code(self, user_prompt: str) -> Tuple[str, float]:
        """
        Request LLM to generate policy_step code for user prompt.
        Returns (raw_extracted_code, latency_seconds).
        """
        start_time = time.perf_counter()
        raw_response = self.client.generate(user_prompt, system_prompt=SYSTEM_PROMPT)
        latency = time.perf_counter() - start_time

        clean_code = self._extract_code(raw_response)
        return clean_code, latency

    def _extract_code(self, raw_response: str) -> str:
        """Extract Python code string from JSON or Markdown block."""
        import json

        # 1. Try direct JSON parse
        try:
            data = json.loads(raw_response)
            if isinstance(data, dict) and "code" in data:
                return data["code"].strip()
        except Exception:
            pass

        # 2. Try JSON markdown block ```json ... ```
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_response, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                if isinstance(data, dict) and "code" in data:
                    return data["code"].strip()
            except Exception:
                pass

        # 3. Try Python markdown block ```python ... ```
        code_match = re.search(r"```(?:python)?\s*(.*?)\s*```", raw_response, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()

        # 4. Regex fallback for "code": "..."
        field_match = re.search(r'"code"\s*:\s*"(.*?)(?<!\\)"', raw_response, re.DOTALL)
        if field_match:
            raw_field = field_match.group(1)
            return raw_field.encode("utf-8").decode("unicode_escape").strip()

        # 5. Look for def policy_step directly in response
        if "def policy_step" in raw_response:
            pos = raw_response.find("def policy_step")
            return raw_response[pos:].strip()

        return raw_response.strip()

    def create_agent_from_prompt(
        self,
        user_prompt: str,
        agent_name: str = "LLMPlayer"
    ) -> Tuple[CodePolicyAgent, float, Optional[str]]:
        """
        End-to-End prompt to verified CodePolicyAgent pipeline:
        1. Query LLM client
        2. Clean code
        3. Validate AST whitelist security
        4. Wrap into CodePolicyAgent (with fail-safe fallback on security error)
        Returns (agent, latency, error_message_if_any).
        """
        code_str, latency = self.generate_policy_code(user_prompt)

        # AST Security Validation
        is_valid, error = validate_policy_ast(code_str)
        if not is_valid:
            # Fail-safe agent that safely stops
            fallback_code = "def policy_step(state: State) -> ActionCommand:\n    return stop()"
            fallback_agent = CodePolicyAgent(code_str=fallback_code, agent_name=f"{agent_name}_FailSafe")
            return fallback_agent, latency, f"AST Security Check Failed: {error}"

        try:
            agent = CodePolicyAgent(code_str=code_str, agent_name=agent_name)
            return agent, latency, None
        except Exception as e:
            fallback_code = "def policy_step(state: State) -> ActionCommand:\n    return stop()"
            fallback_agent = CodePolicyAgent(code_str=fallback_code, agent_name=f"{agent_name}_FailSafe")
            return fallback_agent, latency, f"Agent Instantiation Failed: {e}"
