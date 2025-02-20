# Copyright (c) 2008, Aldo Cortesi. All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
from libqtile.command.base import expose_command
from libqtile.layout.base import Layout, _ClientList


class _WinStack(_ClientList):
    # shortcuts for current client and index used in Columns layout
    cw = _ClientList.current_client

    def __init__(self, autosplit=False):
        _ClientList.__init__(self)
        self.split = autosplit

    def toggle_split(self):
        self.split = False if self.split else True

    def __str__(self):
        return "_WinStack: %s, %s" % (self.cw, str([client.name for client in self.clients]))

    @expose_command()
    def info(self):
        info = _ClientList.info(self)
        info["split"] = self.split
        return info


class Stack(Layout):
    """A layout composed of stacks of windows

    The stack layout divides the screen_rect horizontally into a set of stacks.
    Commands allow you to switch between stacks, to next and previous windows
    within a stack, and to split a stack to show all windows in the stack, or
    unsplit it to show only the current window.

    Unlike the columns layout the number of stacks is fixed.
    """

    defaults = [
        ("border_focus", "#0000ff", "Border colour(s) for the focused window."),
        ("border_normal", "#000000", "Border colour(s) for un-focused windows."),
        (
            "border_focus_stack",
            None,
            "Border colour(s) for the focused stacked window. If 'None' will \
         default to border_focus.",
        ),
        (
            "border_normal_stack",
            None,
            "Border colour(s) for un-focused stacked windows. If 'None' will \
         default to border_normal.",
        ),
        ("border_width", 1, "Border width."),
        ("autosplit", False, "Auto split all new stacks."),
        ("num_stacks", 2, "Number of stacks."),
        ("fair", False, "Add new windows to the stacks in a round robin way."),
        ("margin", 0, "Margin of the layout (int or list of ints [N E S W])"),
    ]

    def __init__(self, **config):
        Layout.__init__(self, **config)
        self.add_defaults(Stack.defaults)
        if self.num_stacks <= 0:
            # Catch stupid mistakes early and generate a useful message
            raise ValueError("num_stacks must be at least 1")
        self.stacks = [_WinStack(autosplit=self.autosplit) for i in range(self.num_stacks)]

    @property
    def current_stack(self):
        return self.stacks[self.current_stack_offset]

    @property
    def current_stack_offset(self):
        for i, s in enumerate(self.stacks):
            if self.group.current_window in s:
                return i
        return 0

    @property
    def clients(self):
        client_list = []
        for stack in self.stacks:
            client_list.extend(stack.clients)
        return client_list

    def clone(self, group):
        c = Layout.clone(self, group)
        # These are mutable
        c.stacks = [_WinStack(autosplit=self.autosplit) for i in self.stacks]
        return c

    def _find_next(self, lst, offset):
        for i in lst[offset + 1 :]:
            if i:
                return i
        for i in lst[:offset]:
            if i:
                return i

    def delete_current_stack(self):
        if len(self.stacks) > 1:
            off = self.current_stack_offset or 0
            s = self.stacks[off]
            self.stacks.remove(s)
            off = min(off, len(self.stacks) - 1)
            self.stacks[off].join(s, 1)
            if self.stacks[off]:
                self.group.focus(self.stacks[off].cw, False)

    def next_stack(self):
        n = self._find_next(self.stacks, self.current_stack_offset)
        if n:
            self.group.focus(n.cw, True)

    def previous_stack(self):
        n = self._find_next(
            list(reversed(self.stacks)), len(self.stacks) - self.current_stack_offset - 1
        )
        if n:
            self.group.focus(n.cw, True)

    def focus(self, client):
        for i in self.stacks:
            if client in i:
                i.focus(client)

    def focus_first(self):
        for i in self.stacks:
            if i:
                return i.focus_first()

    def focus_last(self):
        for i in reversed(self.stacks):
            if i:
                return i.focus_last()

    def focus_next(self, client):
        iterator = iter(self.stacks)
        for i in iterator:
            if client in i:
                next = i.focus_next(client)
                if next:
                    return next
                break
        else:
            return

        for i in iterator:
            if i:
                return i.focus_first()

    def focus_previous(self, client):
        iterator = iter(reversed(self.stacks))
        for i in iterator:
            if client in i:
                next = i.focus_previous(client)
                if next:
                    return next
                break
        else:
            return

        for i in iterator:
            if i:
                return i.focus_last()

    def add_client(self, client):
        for i in self.stacks:
            if not i:
                i.add_client(client)
                return
        if self.fair:
            target = min(self.stacks, key=len)
            target.add_client(client)
        else:
            self.current_stack.add_client(client)

    def remove(self, client):
        current_offset = self.current_stack_offset
        for i in self.stacks:
            if client in i:
                i.remove(client)
                break
        if self.stacks[current_offset].cw:
            return self.stacks[current_offset].cw
        else:
            n = self._find_next(
                list(reversed(self.stacks)), len(self.stacks) - current_offset - 1
            )
            if n:
                return n.cw

    def configure(self, client, screen_rect):
        # pylint: disable=undefined-loop-variable
        # We made sure that self.stacks is not empty, so s is defined.
        for i, s in enumerate(self.stacks):
            if client in s:
                break
        else:
            client.hide()
            return

        if client.has_focus:
            if self.border_focus_stack:
                if s.split:
                    px = self.border_focus
                else:
                    px = self.border_focus_stack
            else:
                px = self.border_focus
        else:
            if self.border_normal_stack:
                if s.split:
                    px = self.border_normal
                else:
                    px = self.border_normal_stack
            else:
                px = self.border_normal

        column_width = int(screen_rect.width / len(self.stacks))
        xoffset = screen_rect.x + i * column_width
        window_width = column_width - 2 * self.border_width

        if s.split:
            column_height = int(screen_rect.height / len(s))
            window_height = column_height - 2 * self.border_width
            yoffset = screen_rect.y + s.index(client) * column_height
            client.place(
                xoffset,
                yoffset,
                window_width,
                window_height,
                self.border_width,
                px,
                margin=self.margin,
            )
            client.unhide()
        else:
            if client == s.cw:
                client.place(
                    xoffset,
                    screen_rect.y,
                    window_width,
                    screen_rect.height - 2 * self.border_width,
                    self.border_width,
                    px,
                    margin=self.margin,
                )
                client.unhide()
            else:
                client.hide()

    def get_windows(self):
        return self.clients

    @expose_command()
    def info(self):
        d = Layout.info(self)
        d["stacks"] = [i.info() for i in self.stacks]
        d["current_stack"] = self.current_stack_offset
        d["clients"] = [c.name for c in self.clients]
        return d

    @expose_command()
    def toggle_split(self):
        """Toggle vertical split on the current stack"""
        self.current_stack.toggle_split()
        self.group.layout_all()

    @expose_command()
    def down(self):
        """Switch to the next window in this stack"""
        self.current_stack.current_index += 1
        self.group.focus(self.current_stack.cw, False)

    @expose_command()
    def up(self):
        """Switch to the previous window in this stack"""
        self.current_stack.current_index -= 1
        self.group.focus(self.current_stack.cw, False)

    @expose_command()
    def shuffle_up(self):
        """Shuffle the order of this stack up"""
        self.current_stack.shuffle_up()
        self.group.layout_all()

    @expose_command()
    def shuffle_down(self):
        """Shuffle the order of this stack down"""
        self.current_stack.shuffle_down()
        self.group.layout_all()

    @expose_command()
    def delete(self):
        """Delete the current stack from the layout"""
        self.delete_current_stack()

    @expose_command()
    def add(self):
        """Add another stack to the layout"""
        newstack = _WinStack(autosplit=self.autosplit)
        if self.autosplit:
            newstack.split = True
        self.stacks.append(newstack)
        self.group.layout_all()

    @expose_command()
    def rotate(self):
        """Rotate order of the stacks"""
        if self.stacks:
            self.stacks.insert(0, self.stacks.pop())
        self.group.layout_all()

    @expose_command()
    def next(self):
        """Focus next stack"""
        return self.next_stack()

    @expose_command()
    def previous(self):
        """Focus previous stack"""
        return self.previous_stack()

    @expose_command()
    def client_to_next(self):
        """Send the current client to the next stack"""
        return self.client_to_stack(self.current_stack_offset + 1)

    @expose_command()
    def client_to_previous(self):
        """Send the current client to the previous stack"""
        return self.client_to_stack(self.current_stack_offset - 1)

    @expose_command()
    def client_to_stack(self, n):
        """
        Send the current client to stack n, where n is an integer offset.  If
        is too large or less than 0, it is wrapped modulo the number of stacks.
        """
        if not self.current_stack:
            return
        next = n % len(self.stacks)
        win = self.current_stack.cw
        self.current_stack.remove(win)
        self.stacks[next].add_client(win)
        self.stacks[next].focus(win)
        self.group.layout_all()
