"""Exercise the real send boundary with NoneBot's actual finish exception."""
import unittest
from unittest.mock import AsyncMock

from nonebot.exception import FinishedException

from tests.bootstrap import p
from nonebot_plugin_alconna import UniMessage


class CardFallbackTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.matcher = type('Matcher', (), {'send': AsyncMock(), 'finish': AsyncMock(side_effect=FinishedException)})

    async def test_image_sent_once_without_placeholder_fallback(self):
        with self.assertRaises(FinishedException):
            await p._send_card_or_text(self.matcher, b'png', 'complete text')
        self.matcher.send.assert_awaited_once()
        self.assertIsInstance(self.matcher.send.call_args.args[0], UniMessage)
        self.assertEqual(self.matcher.send.call_args.kwargs, {'fallback': False})
        self.matcher.finish.assert_awaited_once_with()

    async def test_export_or_send_error_returns_complete_text(self):
        for error in (ValueError('unsupported image'), RuntimeError('upload failed')):
            with self.subTest(error=error):
                self.matcher.send.reset_mock()
                self.matcher.finish.reset_mock()
                self.matcher.send.side_effect = error
                with self.assertRaises(FinishedException):
                    await p._send_card_or_text(self.matcher, b'png', 'complete text')
                self.matcher.finish.assert_awaited_once_with('complete text')

    async def test_text_send_failure_is_not_retried(self):
        self.matcher.send.side_effect = RuntimeError('upload failed')
        self.matcher.finish.side_effect = OSError('text send failed')
        with self.assertRaises(OSError):
            await p._send_card_or_text(self.matcher, b'png', 'complete text')
        self.matcher.finish.assert_awaited_once_with('complete text')
