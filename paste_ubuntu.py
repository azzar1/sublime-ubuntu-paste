import pwd
import sublime
import sublime_plugin
import threading
import urllib

from .lib.thread_progress import ThreadProgress
from .lib.syntax_items import syntax_items

HOSTNAME = 'http://paste.ubuntu.com'
POST_POSTER_FIELD = 'poster'
POST_SYNTAX_FIELD = 'syntax'
POST_CONTENT_FIELD = "content"
NEWLINE = '\r\n'


class PasteUbuntuCommand(sublime_plugin.WindowCommand):

    def run_command(self, command, callback=None, **kwargs):
        thread = ThreadCommand(command, callback, **kwargs)
        thread.start()
        ThreadProgress(thread, kwargs.get('status_message', False)
                       or ' '.join(command), '')

    def run(self):
        self.get_poster()

    def get_poster(self):
        self.window.show_input_panel("Poster:", self.guess_username(),
                                     self.get_syntax, None, None)

    def guess_username(self):
        return pwd.getpwuid(os.getuid())[0]

    def get_syntax(self, poster):
        if not poster:
            return

        self.poster = poster
        self.window.show_quick_panel(syntax_items, self.send_request_async)

    def send_request_async(self, syntax):
        if syntax < 0:
            return

        self.syntax = syntax_items[syntax][0]

        thread = threading.Thread(target=self.send_request_sync)
        thread.start()
        ThreadProgress(thread, "Pasting content to paste.ubuntu.com",
                       'Complted! Check your clipboard.')

    def send_request_sync(self):
        self.content = self.get_content()

        if not self.content:
            return

        body = {POST_POSTER_FIELD: self.poster,
                POST_SYNTAX_FIELD: self.syntax,
                POST_CONTENT_FIELD: self.content}

        binary_bode = urllib.parse.urlencode(body).encode('utf-8')

        request = urllib.request.Request(
            url=HOSTNAME, headers={'Content-Type': 'text/html'}, data=binary_bode)
        reply = urllib.request.urlopen(request).geturl()

        if reply == HOSTNAME:
            sublime.set_clipboard("Something went wrong. Try again.")
        else:
            sublime.set_clipboard(reply)

    def get_content(self):
        content = self.get_selection_content()

        # if we haven't gotten data from selected text,
        # we assume the entire file should be pasted:
        if not content:
            content = self.get_view_content()

        return content

    def get_selection_content(self):
        view = self.view()
        if not view:
            return

        content = u''

        for region in view.sel():
            if not region.empty():
                # be sure to insert a newline if we have multiple selections
                if content:
                    content += NEWLINE
                content += view.substr(region)

        return content

    def get_view_content(self):
        view = self.view()
        if not view:
            return

        return view.substr(sublime.Region(0, view.size()))

    def view(self):
        if not self.window:
            return
        return self.window.active_view()
