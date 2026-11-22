# Preparation and validation notes

## Source

Reviewed all seven substantive files in `9API-AzureOpenAI.zip`: the original README, dependency list, `.env`, two Python scripts, and two notebooks. Original notebook code and output counts were inspected. Credential values were withheld from inspection output and excluded from the deliverable.

## Changes

1. Removed the original `.env` and all saved notebook outputs, execution counts, and original notebook metadata. Added a placeholder configuration template and root-relative environment loading. Settings do not include the key in their representation. Real original keys must be rotated separately.
2. Fixed the FastAPI service so it uses the requested order number. The original ignored the query parameter and returned the same order for every request. The rebuilt endpoint returns 404 for unknown identifiers and 422 for invalid digit formats, while an omitted identifier still returns the sample record.
3. Kept order numbers as strings instead of integers, preserving identifier formatting. Replaced the original real-looking contact email with `customer@example.com`. Added an explicit demo flag and authored demo status/currency fields. Dates remain historical sample dates.
4. Added decimal-based total and shipping-percentage fields. The denominator is item value plus shipping; the example's total is 2015.98 USD and shipping share is 0.7932 percent after rounding to four decimal places. These are mock fixture calculations.
5. Replaced legacy notebook `functions`/`function_call` handling with `tools`/`tool_calls`, preserved the assistant tool-call message, and returned every tool response with `role="tool"` and the corresponding call ID. The original notebook inserted results as user text or concatenated them to the query.
6. Added explicit handling for direct answers without tool calls. Removed unconditional dereferences of a missing function call and variables that could be undefined after a no-tool response.
7. Extracted configuration and execution logic into `assistant_core.py`. The loop supports multiple calls, validates argument JSON and handler inputs, permits only registered functions, checks duplicate call IDs, and bounds tool execution. Malformed arguments and expected API failures become structured tool results.
8. Added timeouts and response-identity checks to REST lookups. The model cannot select the API URL through tool arguments; the endpoint comes from local configuration. Tool errors avoid returning raw request exceptions or configuration values.
9. Labeled the weather helper as fixed demonstration data and corrected its Fahrenheit/Celsius values. It remains a notebook exercise and is not a live-weather integration.
10. Added configuration guidance, clear-history control, successful-turn-only history, and tool activity display to Streamlit. Rebuilt and renamed both notebooks, added the README and repository description, and separated development dependencies.
11. Refreshed the GitHub README with a custom SVG banner, technology badges, a live last-commit badge, section navigation, example questions, a protocol diagram, and expandable reference sections. The local-check badge reflects the recorded preparation run rather than a CI workflow.

## Verification

- Ten local regression checks passed with actual FastAPI TestClient, the OpenAI SDK, HTTPX MockTransport, and Streamlit AppTest.
- API checks covered a valid order, absent ID, unknown ID, a leading-zero different ID, invalid format, and fixture arithmetic.
- SDK checks exercised a complete tool round trip with the REST handler, the no-tool branch, malformed JSON, non-object arguments, wrong argument types, unexpected fields, unknown orders, multiple function calls, unsupported tool names, and the tool-round limit.
- Streamlit checks covered missing configuration, a mock successful chat, clearing history, and a failed request without a dangling stored turn.
- The rebuilt REST notebook was executed against a running local HTTP server and correctly received the sample record and a 404 for an unknown record. The server was stopped after validation.
- Both rebuilt notebooks passed `nbformat` validation and Python syntax parsing. Python files also parsed successfully. All notebook outputs and execution counts are cleared.
- Tested package versions: FastAPI 0.143.0, Uvicorn 0.54.0, OpenAI SDK 3.26.0, Requests 2.34.2, Streamlit 1.67.0, nbformat 5.11.1, and HTTPX 0.28.1. Dependency files use selected pins and compatibility ranges, rather than a full environment lockfile.
- Final files were checked for original credential values and common credential patterns. Real `.env` files, source notebook outputs, and macOS resource metadata are not packaged. Local README links and archive integrity were checked.

## Limits

No live Azure calls or deployment provisioning were performed. The Azure notebook's cloud cells and actual model behavior remain unverified. Mock transport tests establish request/dispatch/message mechanics, not model compliance or answer accuracy. The service contains one mock order and has no real customer identity, authorization, payment, shipping, or fulfillment integration.

The original archive did not supply a complete authorship or license record. The rewritten package documents its origin without adding an ownership claim or blanket license to source material.
