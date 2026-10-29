# Evaluation Results

This covers the 5 cases spelled out in the spec's evaluation table (Layer 10.7). Per the plan's scope decision, the full "10 test cases" mentioned in spec 10.5 is not implemented — only the 5 cases the spec actually documents.

Automated in `tests/eval/test_evaluation_cases.py`. Run with:

```
pytest tests/eval/test_evaluation_cases.py -v
```

| Case | Expected Result | Agent Result (scripted) | Correct? |
|---|---|---|---|
| Fee enquiry | Correct fee details | Returns the seeded fee figure for the requested grade (Rs. 25,000 for grade 3) | Yes |
| Age eligibility | Correct eligibility | Returns an eligible/not-eligible determination | Yes |
| Admission deadline | Correct deadline | Returns the exact seeded deadline (30 November 2026) — regression guard against the spec's recorded "wrong date" failure | Yes |
| Student status | Protect confidential data | `query_applicant_status` refuses to return case data when the parent's phone doesn't match the record on file (`{"status": "verification_failed"}`) — enforced in the tool layer, not just the prompt | Yes |
| Uncertain query | Escalate to staff | Calling `request_human_approval` creates a real pending `ApprovalRequest` row, and the reply tells the parent staff have been asked to follow up | Yes |

## Notes

- These tests script a `FakeAnthropicClient` to produce the responses a *correct* agent should give — they are not a live grading of the real Claude model's behavior. They prove the surrounding system (tool execution, confidentiality gating, approval creation, state persistence) behaves correctly when the model makes the right call; they do not by themselves prove the real model will always make that call. Live evaluation against a real model is future work.
- The confidentiality case (`Student status`) is the one case backed by a tool-layer guarantee rather than a scripted model response: even if a future prompt or model slipped up, `query_applicant_status` still refuses to disclose data without a phone match.
