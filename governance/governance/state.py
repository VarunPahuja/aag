"""The state passed between LangGraph nodes.

LangGraph concept, because this design has to be defensible to a panel: a graph node
is a function that receives the whole state and returns a *partial* update to it.
LangGraph merges each update back into the state. When two keys collide, a reducer
decides what happens — without one, the last write wins.

`opinions` uses `operator.add` as its reducer, which is what makes the fan-out work:
all four agent nodes run from the same entry point, each returns
`{"opinions": [one_opinion]}`, and LangGraph concatenates them instead of having the
fourth agent silently overwrite the first three.
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from shared.contracts import AgentOpinion, Recommendation, TrustEvaluation


class GovernanceState(TypedDict, total=False):
    """What flows through the coordinator graph.

    `evaluation` is read-only input — the trust engine owns those numbers and this lane
    never recomputes them (ADR-0001). No node writes to it.
    """

    evaluation: TrustEvaluation
    mode: str

    # Supplied by the caller, carried through untouched. TrustEvaluation has no identity
    # field of its own, so the link back to it can only come from whoever persists both.
    trust_evaluation_ref: str | None

    # Reducer, not plain assignment — see the module docstring.
    opinions: Annotated[list[AgentOpinion], operator.add]

    # Names of agents whose live call failed and were served from their recording
    # instead. Same reducer and the same reason: four nodes each contribute at most one
    # name, and plain assignment would keep only the last.
    #
    # This exists so the recommendation can say `live+cached` rather than `live`. A
    # recommendation that claimed to be live when a recording answered would be the
    # precise failure this lane exists to prevent — a demo that looks healthy and isn't.
    fell_back: Annotated[list[str], operator.add]

    recommendation: Recommendation
