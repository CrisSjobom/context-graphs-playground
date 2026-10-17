"""Synthetic demonstration data. Not affiliated with a real logistics company."""

from .model import Edge, Graph, Node


def demo_graph() -> Graph:
    nodes = [
        Node("incident-1042", "incident", "Pickup delayed", {"severity": "high", "status": "open"}),
        Node("job-314", "job", "Pickup job #314", {"scheduled_at": "09:30"}),
        Node("vehicle-82", "vehicle", "Vehicle #82", {"type": "motorcycle"}),
        Node("courier-21", "courier", "Courier #21", {"shift": "morning"}),
        Node("zone-north", "zone", "North zone", {"city": "Example City"}),
        Node("event-817", "event", "Assignment changed", {"timestamp": "09:12"}),
        Node("event-819", "event", "Location update missing", {"timestamp": "09:26"}),
        Node("decision-06", "decision", "Reassign pickup", {"reason": "Missed operational checkpoint"}),
        Node("policy-03", "policy", "Late pickup escalation", {"threshold_min": 15}),
        Node("event-821", "event", "Reassignment requested", {"timestamp": "09:47"}),
    ]
    edges = [
        Edge("incident-1042", "job-314", "AFFECTS"),
        Edge("incident-1042", "event-819", "TRIGGERED_BY"),
        Edge("incident-1042", "decision-06", "RESOLVED_THROUGH"),
        Edge("job-314", "vehicle-82", "PICKUP_OF"),
        Edge("job-314", "courier-21", "ASSIGNED_TO"),
        Edge("job-314", "zone-north", "LOCATED_IN"),
        Edge("job-314", "event-817", "HAS_EVENT"),
        Edge("decision-06", "policy-03", "GOVERNED_BY"),
        Edge("decision-06", "event-821", "RESULTED_IN"),
        Edge("event-819", "courier-21", "OBSERVED_FOR"),
    ]
    return Graph(nodes, edges)
