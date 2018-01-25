import os
import time
import json
import logging
import requests
import platform
import subprocess
from argparse import ArgumentParser
from websocket import create_connection


class TeamsRTLRunnerBase(object):
    RUNNER_NAME = 'Override Me'

    def __init__(self, teams_path, port, script_path):
        self.teams_path = teams_path
        self.port = port
        self.script_to_inject = script_path
        self.debugger_url = 'http://localhost:{}'.format(port)
        self.window_to_socket = {}       

    def get_name(self):
        raise NotImplementedError('Please implement')

    def get_teams_path(self):
        logging.info('Getting MS-Teams path')

        if not os.path.isfile(self.teams_path):
            logging.error('Could not guess teams path, please pass it manually. tried {}'.format(self.teams_path))
            raise Exception('File Not Found')

        logging.info('Found Teams path - {}'.format(self.teams_path))
        return self.teams_path

    def kill_running_instances(self):
        logging.info('Killing running instances (if any)')
        self._kill_running_instances_override()

    def _kill_running_instances_override(self):
        raise NotImplementedError('Please implement')

    def spawn_new_instance(self, teams_path):
        logging.info('Spawning new instances from path {}'.format(teams_path))
        self._spawn_new_instance_override(teams_path)
        logging.info('Successfully spawned instance -- waiting for new process to initiailize')
        time.sleep(10)

    def _spawn_new_instance_override(self, teams_path):
        raise NotImplementedError('Please implement')

    def inject_script(self, script_path):
        logging.info('Injecting script {}'.format(script_path))
        self._inject_script_override(script_path)
        logging.info('Script injected successfully')

    def _inject_script_override(self, script_path):
        if not os.path.isfile(script_path):
            logging.error('Script file not found at {}'.format(script_path))
            raise Exception('Script file not found')

        chat_window = self._find_chat_window()
        injected = self._try_inject_to_window(chat_window, script_path)
        
        if not injected:
            err = 'Failed injecting to active windows ):'
            logging.error(err)
            raise Exception(err)

    def _find_chat_window(self):
        get_active_windows_endpoint = '{}/json/list'.format(self.debugger_url)
        window_found = False
        while not window_found:
            logging.info('Searching chat window (Switch to any chat in Teams)')
            res = requests.get(get_active_windows_endpoint)
            if res.status_code != 200:
                logging.error('Got invalid response from {}; status = {} res = {}'.format(
                    get_active_windows_endpoint, res.status_code, res.text))
                raise Exception('Invalid response')

            active_windows = res.json()
            if not active_windows:
                logging.error('Did not get any active windows from {}'.format(
                    get_active_windows_endpoint))
                raise Exception('No active windows')


            for active_window in active_windows:
                title = active_window['title']
                uid = active_window['id']
                ws = self.window_to_socket.get(uid, None)
                if not ws:
                    websocket_url = active_window.get('webSocketDebuggerUrl', 'ws://localhost:{}/devtools/page/{}'.format(self.port, uid))
                    self.window_to_socket[uid] = ws = create_connection(websocket_url, timeout=30)
                payload = self.get_eval_expression("document.querySelectorAll('.ts-edit-box .cke_editable').length")
                ws.send(json.dumps(payload))
                window_found = json.loads(ws.recv())['result']['result']['value'] > 0
                if window_found:
                    logging.info('Found chat window - {}'.format(title))
                    return active_window

            if not window_found:
                logging.info('Chat window not found - Will retry')
                time.sleep(2)

    def _try_inject_to_window(self, chat_window, script_path):
        injected = False
        title = chat_window['title']
        try:
            logging.info('Injecting to {}'.format(title))
            ws = self.window_to_socket[chat_window['id']]
            with open(script_path, 'rb') as f:
                payload = self.get_eval_expression(f.read())
            ws.send(json.dumps(payload))

            res = json.loads(ws.recv()).get('result', {})
            if not res or res.get('exceptionDetails', None):
                error = res.get('exceptionDetails', {}).get('exception', {})
                logging.warn('Failed injecting script {} to window {} due to {}; Continuing to next window'.format(
                    script_path, title, error))
            else:
                injected = True
        except Exception as e:
            logging.warn('Failed for window {}; Continuing'.format(title))
        return injected

    def get_eval_expression(self, expression):
        return {'id': 1337,
                'method': "Runtime.evaluate",
                'params': {'expression': expression,
                           'objectGroup': 'evalme',
                           'returnByValue': False,
                           'userGesture': True}}

    def run(self):
        logging.info('Running with {}'.format(self.get_name()))
        self.kill_running_instances()
        path = self.get_teams_path()
        self.spawn_new_instance(path)
        self.inject_script(self.script_to_inject)
        logging.info('Done ! (Contact dashemes for suggestions / problems)')
        logging.info('Keep window open to ensure persistency (Just in case)')
        while True:
            self.inject_script(self.script_to_inject)
            # Inject every 2 minutes
            time.sleep(60 * 2)



class WindowsTeamsRTLRunner(TeamsRTLRunnerBase):
    def __init__(self, teams_path, port, script_to_inject):
        teams_path = teams_path or os.path.join(os.path.expandvars('%LOCALAPPDATA%'), 'Microsoft', 'Teams', 'Update.exe')
        super(WindowsTeamsRTLRunner, self).__init__(teams_path, port, script_to_inject)

    def get_name(self):
        return 'Windows Teams Script Injector'

    def _kill_running_instances_override(self):
        subprocess.Popen('taskkill /f /im Teams.exe', shell=True).wait()

    def _spawn_new_instance_override(self, teams_path):
        # Throws on error
        subprocess.Popen([teams_path, '--processStart', "Teams.exe",
                          '--process-start-args', '--remote-debugging-port={}'.format(self.port)], cwd=os.path.dirname(teams_path))


class MacTeamsRTLRunner(TeamsRTLRunnerBase):
    def __init__(self, teams_path, port, script_to_inject):
        teams_path = teams_path or '/Applications/Microsoft Teams.app/Contents/MacOS/Teams'
        super(MacTeamsRTLRunner, self).__init__(teams_path, port, script_to_inject)

    def get_name(self):
        return 'Mac Teams Script Injector'

    def _kill_running_instances_override(self):
        subprocess.Popen('killall Teams', shell=True).wait()

    def _spawn_new_instance_override(self, teams_path):
        subprocess.Popen([teams_path, '--remote-debugging-port={}'.format(self.port)], cwd=os.path.dirname(teams_path))



if '__main__' == __name__:
    logging.basicConfig(level=logging.INFO)
    
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=19990,
                        help='Choose an open port (Used for electron debugging)')
    parser.add_argument('-s', '--script', default=os.path.join(
        os.path.dirname(__file__), 'rtl.js'), help='Path of a script to inject')
    parser.add_argument('--teams_path', default=None, help='Path to microsoft teams')
    args = parser.parse_args()

    current_os = platform.system().lower()
    if current_os == 'windows':
        WindowsTeamsRTLRunner(args.teams_path, args.port, args.script).run()
    elif current_os == 'darwin':
        MacTeamsRTLRunner(args.teams_path, args.port, args.script).run()
    else:
        err = 'Unsupported operating system - Will only work on Windows / Mac'
        logging.error(err)
        raise Exception(err)
