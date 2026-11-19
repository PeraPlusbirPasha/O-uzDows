"""Yalnızca yerel X11 smoke testlerinin ICCCM isteği; üretim kodu değildir."""


def request_minimize(monitor, identifier):
    from Xlib import X, Xutil
    from Xlib.protocol import event

    # python-xlib Window.iconify sağlamaz. ICCCM, istemciyi doğrudan
    # unmap etmeyi değil pencere yöneticisine WM_CHANGE_STATE yollamayı ister.
    request = event.ClientMessage(window=identifier,
        client_type=monitor.connection.intern_atom('WM_CHANGE_STATE'),
        data=(32, [Xutil.IconicState, 0, 0, 0, 0]))
    monitor.root.send_event(request, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
    monitor.connection.flush()
