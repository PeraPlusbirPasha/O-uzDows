import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from x11_smoke import request_minimize


class X11SmokeTests(unittest.TestCase):
    def test_minimize_sends_a_real_icccm_client_message_to_the_wm(self):
        try:
            from Xlib import X, Xutil
        except ImportError:
            self.skipTest('python3-xlib yok; CI gerçek Xlib istek kodlamasını sınar')
        monitor = SimpleNamespace(root=Mock(), connection=Mock())
        monitor.connection.intern_atom.return_value = 456
        request_minimize(monitor, 123)
        monitor.connection.intern_atom.assert_called_once_with('WM_CHANGE_STATE')
        args, kwargs = monitor.root.send_event.call_args
        message, = args
        self.assertEqual(message.type, X.ClientMessage)
        self.assertEqual(message.window, 123)
        self.assertEqual(message.client_type, 456)
        self.assertEqual(message.data, (32, [Xutil.IconicState, 0, 0, 0, 0]))
        self.assertEqual(len(message._binary), 32, 'Gerçek python-xlib olayı tel biçimine kodlanmalı')
        self.assertEqual(kwargs, {'event_mask': X.SubstructureRedirectMask | X.SubstructureNotifyMask})
        monitor.connection.flush.assert_called_once_with()
        monitor.connection.create_resource_object.assert_not_called()


if __name__ == '__main__':
    unittest.main()
