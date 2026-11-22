"""Offline API, SDK protocol, and UI checks. No Azure account is contacted."""
import json
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
import httpx
from openai import AzureOpenAI
import requests

from GET_JSON import app
from assistant_core import (ROOT, ORDER_TOOLS, WEATHER_TOOLS, ChatResult, LookupFailure,
                            Settings, get_demo_weather, get_order_details, run_tool_chat)


def call(name="get_order_details", arguments='{"order_number":"123456789"}', call_id="call_1"):
    return {"id": call_id, "type": "function", "function": {"name": name, "arguments": arguments}}


def completion(content=None, calls=None):
    message = {"role": "assistant", "content": content}
    if calls:
        message["tool_calls"] = calls
    return {"id": "offline", "object": "chat.completion", "created": 0, "model": "offline",
            "choices": [{"index": 0, "finish_reason": "tool_calls" if calls else "stop", "message": message}]}


class LocalTests(unittest.TestCase):
    def setUp(self):
        self.api = TestClient(app)
        self.addCleanup(self.api.close)

    def sdk(self, responses):
        self.requests = []
        iterator = iter(responses)
        def handler(request):
            self.requests.append(json.loads(request.content))
            return httpx.Response(200, json=next(iterator))
        client = AzureOpenAI(api_key="offline-test-key", azure_endpoint="https://offline.invalid/",
            api_version="2024-10-21", max_retries=0,
            http_client=httpx.Client(transport=httpx.MockTransport(handler)))
        self.addCleanup(client.close)
        return client

    def bridge(self, url, params, timeout):
        self.assertEqual(timeout, 15)
        actual = self.api.get("/test", params=params)
        response = requests.Response()
        response.status_code = actual.status_code
        response._content = actual.content
        response.url = url
        return response

    def test_api_matches_identifier_and_computes_totals(self):
        response = self.api.get("/test", params={"order_number": "123456789"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["OrderTotal"], 2015.98)
        self.assertEqual(data["ShippingPercentageOfTotal"], 0.7932)
        self.assertEqual(data["Email"], "customer@example.com")
        self.assertEqual(self.api.get("/test").status_code, 200)
        self.assertEqual(self.api.get("/test?order_number=999999999").status_code, 404)
        self.assertEqual(self.api.get("/test?order_number=000123456789").status_code, 404)
        self.assertEqual(self.api.get("/test?order_number=abc").status_code, 422)

    def test_lookup_validates_arguments_and_backend_record(self):
        with patch("assistant_core.requests.get", side_effect=self.bridge):
            self.assertEqual(get_order_details("123456789")["OrderNumber"], "123456789")
            with self.assertRaises(LookupFailure) as error:
                get_order_details("999999999")
            self.assertEqual(error.exception.code, "order_not_found")
        for invalid in [123456789, True, "", "12abc", "1" * 33]:
            with self.assertRaises(ValueError):
                get_order_details(invalid)
        with patch("assistant_core.requests.get", side_effect=requests.Timeout):
            with self.assertRaises(LookupFailure) as error:
                get_order_details("123456789")
            self.assertEqual(error.exception.code, "api_unavailable")
        with patch("assistant_core.requests.get") as get:
            get.return_value.status_code = 200
            get.return_value.json.return_value = {"OrderNumber": "different"}
            with self.assertRaises(LookupFailure):
                get_order_details("123456789")

    def test_full_order_tool_protocol_with_real_sdk(self):
        client = self.sdk([completion(calls=[call()]), completion("The demo delivery date is July 28, 2024.")])
        with patch("assistant_core.requests.get", side_effect=self.bridge):
            result = run_tool_chat("When will my order arrive?", client=client, deployment="offline-chat",
                tools=ORDER_TOOLS, handlers={"get_order_details": get_order_details})
        self.assertIn("2024", result.answer)
        messages = self.requests[1]["messages"]
        self.assertEqual([m["role"] for m in messages], ["system", "user", "assistant", "tool"])
        self.assertEqual(messages[-1]["tool_call_id"], messages[-2]["tool_calls"][0]["id"])
        self.assertEqual(json.loads(messages[-1]["content"])["OrderNumber"], "123456789")
        self.assertEqual(len(result.tool_events), 1)

    def test_direct_answer_skips_tools(self):
        client = self.sdk([completion("A REST API exposes resources over HTTP.")])
        with patch("assistant_core.get_order_details", side_effect=AssertionError("No lookup expected")) as lookup:
            result = run_tool_chat("Explain REST", client=client, deployment="offline-chat",
                tools=ORDER_TOOLS, handlers={"get_order_details": lookup})
        self.assertEqual(result.tool_events, [])
        self.assertEqual(len(self.requests), 1)

    def test_invalid_tool_json_and_extra_fields_become_errors(self):
        for arguments in ["{broken", "[]", '{"order_number":123}', '{"order_number":"123456789","extra":1}']:
            with self.subTest(arguments=arguments):
                client = self.sdk([completion(calls=[call(arguments=arguments)]), completion("Please provide a valid order identifier.")])
                result = run_tool_chat("Look up an order", client=client, deployment="offline-chat",
                    tools=ORDER_TOOLS, handlers={"get_order_details": get_order_details})
                self.assertEqual(result.tool_events[0]["result"]["error"]["code"], "invalid_arguments")

    def test_unknown_order_is_a_tool_error(self):
        client = self.sdk([completion(calls=[call(arguments='{"order_number":"999999999"}')]), completion("That demo order was not found.")])
        with patch("assistant_core.requests.get", side_effect=self.bridge):
            result = run_tool_chat("Find order 999999999", client=client, deployment="offline-chat",
                tools=ORDER_TOOLS, handlers={"get_order_details": get_order_details})
        self.assertEqual(result.tool_events[0]["result"]["error"]["code"], "order_not_found")

    def test_multiple_calls_have_matching_tool_results(self):
        calls = [call("get_demo_weather", '{"location":"Paro","unit":"celsius"}', "weather_1"),
                 call("get_demo_weather", '{"location":"Boston"}', "weather_2")]
        client = self.sdk([completion(calls=calls), completion("These are fixed demo temperatures.")])
        result = run_tool_chat("Show two demo locations", client=client, deployment="offline-chat",
            tools=WEATHER_TOOLS, handlers={"get_demo_weather": get_demo_weather})
        self.assertEqual([m["tool_call_id"] for m in self.requests[1]["messages"][-2:]], ["weather_1", "weather_2"])
        self.assertEqual(result.tool_events[0]["result"]["temperature"], 22.2)
        self.assertEqual(result.tool_events[1]["result"]["temperature"], 72)

    def test_unsupported_tool_and_round_limit(self):
        client = self.sdk([completion(calls=[call("not_registered")])])
        with self.assertRaisesRegex(ValueError, "unsupported"):
            run_tool_chat("Query", client=client, deployment="offline-chat", tools=ORDER_TOOLS,
                          handlers={"get_order_details": get_order_details})
        client = self.sdk([completion(calls=[call()]), completion(calls=[call(call_id="call_2")])])
        with patch("assistant_core.requests.get", side_effect=self.bridge):
            with self.assertRaisesRegex(ValueError, "limit"):
                run_tool_chat("Query", client=client, deployment="offline-chat", tools=ORDER_TOOLS,
                              handlers={"get_order_details": get_order_details}, max_tool_rounds=1)
        self.assertEqual(self.requests[-1]["tool_choice"], "none")

    def test_configuration_and_history_validation(self):
        with patch.dict(os.environ, {}, clear=True), patch("dotenv.load_dotenv"):
            with self.assertRaisesRegex(ValueError, "AZURE_OAI"):
                Settings.load()
        self.assertNotIn("offline-test-key", repr(Settings("https://offline.invalid", "offline-test-key", "demo")))
        with self.assertRaisesRegex(ValueError, "history"):
            run_tool_chat("Hi", client=None, deployment="offline", tools=ORDER_TOOLS, handlers={},
                          conversation=[{"role": "tool", "content": "invalid history"}])

    def test_streamlit_success_clear_and_failed_turn(self):
        from streamlit.testing.v1 import AppTest
        script = str(ROOT / "app.py")
        with patch.dict(os.environ, {}, clear=True), patch("dotenv.load_dotenv"):
            missing = AppTest.from_file(script).run()
            self.assertFalse(missing.exception)
            self.assertTrue(missing.info)
        settings = Settings("https://offline.invalid/", "offline-test-key", "offline-chat")
        with patch.object(Settings, "load", return_value=settings), \
             patch("assistant_core.answer_order_query", return_value=ChatResult("Demo reply")):
            ui = AppTest.from_file(script).run()
            ui.chat_input[0].set_value("Find order 123456789").run()
            self.assertFalse(ui.exception)
            self.assertEqual([m["role"] for m in ui.session_state["messages"]], ["user", "assistant"])
            ui.sidebar.button[0].click().run()
            self.assertEqual(ui.session_state["messages"], [])
        with patch.object(Settings, "load", return_value=settings), \
             patch("assistant_core.answer_order_query", side_effect=ValueError("Offline failure")):
            ui = AppTest.from_file(script).run()
            ui.chat_input[0].set_value("Try again").run()
            self.assertTrue(ui.error)
            self.assertEqual(ui.session_state["messages"], [])


if __name__ == "__main__":
    unittest.main()
