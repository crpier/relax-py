import contextlib
import time
from socket import AF_UNIX, SOCK_STREAM, socket
import uvicorn.config
from uvicorn.supervisors.watchfilesreload import WatchFilesReload
import uvicorn
import json
from pathlib import Path

from relax.config import BaseConfig
from relax.injection import COMPONENTS_CACHE_FILE


from typing import (
    Callable,
)

MAX_CONNECT_RETRIES = 5


class RelaxReload(WatchFilesReload):
    base_config: BaseConfig

    def __init__(
        self,
        config: uvicorn.config.Config,
        target: Callable[[list[socket] | None], None],
        sockets: list[socket],
        base_config: BaseConfig,
    ) -> None:
        super().__init__(config, target, sockets)
        self.base_config = base_config
        self._reload_socket: socket | None = None

    def should_restart(self) -> list[Path] | None:
        try:
            changed_paths = super().should_restart()
            if changed_paths is None:
                return None
            changed_templates: list[Path] = []
            changed_app_files: list[Path] = []
            for change in changed_paths:
                try:
                    Path(change).relative_to(self.base_config.TEMPLATES_DIR)
                    changed_templates.append(Path(change).relative_to(Path.cwd()))
                # we raise ValueError if the path is not in the templates dir
                except ValueError:
                    changed_app_files.append(change)
            if len(changed_app_files) > 0:
                print("changed app files: ", changed_app_files)
                return changed_app_files
            if len(changed_templates) > 0:
                print("changed templates: ", changed_templates)
                self._update_templates(changed_templates)
        except Exception as e:
            print("failed to check for restart: %s" % e)
            raise
        return None

    def shutdown(self) -> None:
        if self.reload_socket is not None:
            self.reload_socket.close()
        return super().shutdown()

    def run(self, *, remove_components_cache_on_startup: bool = True) -> None:
        if remove_components_cache_on_startup:
            with contextlib.suppress(FileNotFoundError):
                COMPONENTS_CACHE_FILE.unlink()
            with COMPONENTS_CACHE_FILE.open("w") as f:
                json.dump({}, f)
        return super().run()

    def get_new_reload_socket(self, retries: int = 0) -> socket:
        self.reload_socket = socket(AF_UNIX, SOCK_STREAM)
        self.reload_socket.settimeout(5)
        try:
            self.reload_socket.connect(str(self.base_config.RELOAD_SOCKET_PATH))
        except ConnectionRefusedError:
            if retries >= MAX_CONNECT_RETRIES:
                raise
            time.sleep(1)
            return self.get_new_reload_socket(retries + 1)
        return self.reload_socket

    def _update_templates(self, changed_templates: list[Path]) -> None:
        try:
            if self._reload_socket is None:
                self.get_new_reload_socket()
        except ConnectionRefusedError:
            print("can't connect to reload socket, not updating templates")
            return
        changes = json.dumps(
            {
                "event_type": "update_views",
                "data": [str(change) for change in changed_templates],
            },
        ).encode()
        self.reload_socket.send(changes)
        self.reload_socket.close()


def start_app(
    app_path: str,
    config: BaseConfig,
    *,
    host: str = "127.0.0.1",
    port: int | None = None,
    reload: bool = False,
    log_level: str = "info",
) -> None:
    if port is None:
        port = config.PORT

    server_config = uvicorn.Config(
        app=app_path,
        host=host,
        port=port,
        log_level=log_level,
        factory=True,
    )

    server = uvicorn.Server(server_config)

    if reload:
        reload_config = uvicorn.Config(
            app=app_path,
            host=host,
            port=port,
            factory=True,
            reload=True,
            log_level=log_level,
        )
        sock = reload_config.bind_socket()
        reloader = RelaxReload(
            reload_config,
            target=server.run,
            sockets=[sock],
            base_config=config,
        )
        reloader.run()
    else:
        server.run()
