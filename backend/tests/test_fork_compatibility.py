"""Regression cases for the behavior retained by this fork.

Run with an isolated application data directory, as with the upstream backend.
"""

import copy
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from open_webui.routers import chats, openai


class ReasoningToolsTests(unittest.TestCase):
    def setUp(self):
        self.payload = {
            'model': 'gpt-5.5',
            'reasoning_effort': 'high',
            'messages': [{'role': 'user', 'content': 'Read the working directory.'}],
            'tools': [{'type': 'function', 'function': {'name': 'list_files', 'parameters': {'type': 'object'}}}],
        }

    def test_reasoning_with_tools_uses_responses_for_openai(self):
        self.assertTrue(openai.should_use_responses_for_reasoning_tools('https://api.openai.com/v1', self.payload))

    def test_other_providers_and_lookalike_hosts_are_not_rerouted(self):
        for url in ['https://example.com/v1', 'https://api.openai.com.example.com/v1', 'https://example.com/api.openai.com']:
            with self.subTest(url=url):
                self.assertFalse(openai.should_use_responses_for_reasoning_tools(url, self.payload))

    def test_request_without_tools_or_reasoning_keeps_its_api(self):
        for field in ['tools', 'reasoning_effort']:
            payload = copy.deepcopy(self.payload)
            payload.pop(field)
            with self.subTest(field=field):
                self.assertFalse(openai.should_use_responses_for_reasoning_tools('https://api.openai.com/v1', payload))

    def test_responses_conversion_preserves_reasoning_and_function(self):
        converted = openai.convert_to_responses_payload(copy.deepcopy(self.payload))
        self.assertEqual(converted['reasoning']['effort'], 'high')
        self.assertNotIn('reasoning_effort', converted)
        self.assertEqual(converted['tools'][0]['name'], 'list_files')
        self.assertEqual(converted['input'][0]['content'][0]['text'], 'Read the working directory.')

    def test_explicit_reasoning_effort_is_preserved(self):
        payload = {**copy.deepcopy(self.payload), 'reasoning': {'effort': 'low', 'summary': 'auto'}}
        self.assertEqual(openai.convert_to_responses_payload(payload)['reasoning'], {'effort': 'low', 'summary': 'auto'})


class SharedChatAccessTests(unittest.IsolatedAsyncioTestCase):
    async def test_private_share_denies_ungranted_user(self):
        with patch.object(chats.AccessGrants, 'has_access', new=AsyncMock(return_value=False)):
            self.assertFalse(await chats.can_read_shared_chat(SimpleNamespace(id='reader', role='user'), SimpleNamespace(user_id='owner', chat_id='private-chat'), db=None))

    async def test_share_owner_keeps_access(self):
        self.assertTrue(await chats.can_read_shared_chat(SimpleNamespace(id='owner', role='user'), SimpleNamespace(user_id='owner', chat_id='private-chat'), db=None))

    async def test_pending_account_is_not_treated_as_a_verified_reader(self):
        self.assertFalse(await chats.can_read_shared_chat(SimpleNamespace(id='pending', role='pending'), SimpleNamespace(user_id='owner', chat_id='private-chat'), db=None))

    async def test_admin_access_setting_is_respected(self):
        with patch.object(chats, 'ENABLE_ADMIN_CHAT_ACCESS', False), patch.object(chats.AccessGrants, 'has_access', new=AsyncMock(return_value=False)):
            self.assertFalse(await chats.can_read_shared_chat(SimpleNamespace(id='admin', role='admin'), SimpleNamespace(user_id='owner', chat_id='private-chat'), db=None))


if __name__ == '__main__':
    unittest.main()
