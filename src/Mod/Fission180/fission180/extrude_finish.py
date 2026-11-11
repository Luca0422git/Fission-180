# SPDX-License-Identifier: LGPL-2.1-or-later
"""A dialog that cannot finish says so where the person is looking.

The book parity report's first pattern (about 40 entries): "Extrude OK doing nothing after an
option change", "feature edits that end with a warning were silently not saved". Two things
happened. OK on a dialog whose preview has a problem keeps the dialog open (like Fusion's),
but the warning was already in the dialog, so the click changed nothing on the screen. And a
command started while the dialog was open finishes the dialog first (taskui.Panel.finish: OK,
or Cancel when OK is refused): the edit was dropped without a word.

`SaysWhy` is mixed into the feature dialogs of Extrude, Revolve, Sweep, Loft and the
primitives (Box, Cylinder, Sphere, Torus, Coil); `speaking` wraps the accept() of the ones
with many ways out:

  refuse(text)   OK was pressed and the dialog stays open: the reason in the dialog and next
                 to the mouse (commands.tell), so the click is answered
  finish()       another command starts: OK if possible; else Cancel, saying next to the
                 mouse that the edit was not kept and why
"""

from . import log, warn


def plain(text):
    """A dialog message without its warning sign."""
    text = (text or "").strip()
    return text[1:].strip() if text.startswith("⚠") else text


def not_finished(title, reason):
    """What is said next to the mouse when OK is refused."""
    reason = plain(reason)
    return "%s is not finished: %s" % (title, reason) if reason else "%s is not finished." % title


def dropped(title, reason, editing=False):
    """What is said when another command ended the dialog and its work could not be kept."""
    reason = plain(reason)
    what = "The change to %s was not kept" % title if editing else "%s was not made" % title
    return "%s: %s" % (what, reason) if reason else what + "."


def speaking(accept):
    """Decorator for a dialog's accept(): when OK is refused (accept returns False) the
    reason the dialog shows is also said next to the mouse, so the click is answered. For
    the dialogs whose accept() has many ways out (Revolve, Sweep, Loft, the primitives)."""

    def wrapped(self, *args, **kwargs):
        result = accept(self, *args, **kwargs)
        if result is False and not getattr(self, "_closed", False):
            try:
                self._say(not_finished(self._what(), self.message.text()))
            except Exception:
                pass
        return result

    wrapped.__name__ = getattr(accept, "__name__", "accept")
    wrapped.__doc__ = accept.__doc__
    return wrapped


class SaysWhy:
    """Mixin for a taskui.Panel (before Panel in the bases)."""

    def refuse(self, text):
        """OK cannot finish: say why in the dialog and next to the mouse. Returns False (what
        accept() returns to keep the dialog open)."""
        try:
            self.message.setText("⚠ " + plain(text))
        except Exception:
            pass
        self._say(not_finished(self._what(), text))
        return False

    def worth_saying(self):
        """True when the dialog holds work that a silent Cancel would lose: a step being
        edited, or one with a preview (override for more)."""
        if getattr(self, "editing", False):
            return True
        try:
            return self.feature() is not None
        except Exception:
            return False

    def finish(self):
        """Another command is starting: keep this edit if it is valid; else drop it and say
        so (it was dropped without a word)."""
        self._ending_for_another = True
        try:
            if self.accept():
                return
        finally:
            self._ending_for_another = False
        reason, say = "", False
        try:
            reason = self.message.text()
            say = bool(self.worth_saying())
        except Exception:
            pass
        self.reject()
        if say:
            self._say(dropped(self._what(), reason, bool(getattr(self, "editing", False))))

    def _what(self):
        title = getattr(self, "title", "") or "The command"
        return title[5:] if title.startswith("Edit ") else title

    def _say(self, text):
        if getattr(self, "_ending_for_another", False):
            return  # (finish() says it once, after the dialog closed)
        import time

        last = getattr(self, "_said", None)
        now = time.monotonic()
        if last is not None and last[0] == text and now - last[1] < 0.5:
            return  # (refuse() and the accept wrapper both speak: once is enough)
        self._said = (text, now)
        try:
            from . import commands

            commands.tell(text)
        except Exception as exc:
            warn("could not say %r: %s" % (text, exc))
            log(text)
