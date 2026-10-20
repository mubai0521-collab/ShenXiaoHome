"""Security-boundary checks that do not require Windows or an Android SDK."""

import ast
import asyncio
from contextlib import asynccontextmanager
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from shenxiao_runtime import chat_only_lifespan, upstream_runtime_enabled

ROOT = Path(__file__).resolve().parents[1]
ANDROID = "{http://schemas.android.com/apk/res/android}"


class StartupTests(unittest.IsolatedAsyncioTestCase):
    async def test_default_main_startup_never_enters_upstream_workers(self):
        events = []

        async def initialize():
            events.append("db")

        async def restore():
            events.append("restore")

        async def close():
            events.append("close")

        @asynccontextmanager
        async def forbidden(_app):
            raise AssertionError("upstream worker bundle was started")
            yield

        # Execute the actual entry-point wrapper without importing hardware
        # modules or starting a server as part of test collection.
        tree = ast.parse((ROOT / "aion-chat/main.py").read_text(encoding="utf-8"))
        node = next(item for item in tree.body
                    if isinstance(item, ast.AsyncFunctionDef) and item.name == "lifespan")
        namespace = dict(asynccontextmanager=asynccontextmanager, FastAPI=object,
                         upstream_runtime_enabled=upstream_runtime_enabled,
                         upstream_lifespan=forbidden,
                         chat_only_lifespan=chat_only_lifespan,
                         init_db=initialize, restore_active_windows=restore,
                         close_embedding_client=close)
        exec(compile(ast.Module(body=[node], type_ignores=[]), "main.py", "exec"), namespace)
        with patch.dict(os.environ, {}, clear=True):
            async with namespace["lifespan"](object()):
                events.append("serve")
        self.assertEqual(events, ["db", "restore", "serve", "close"])

    async def test_startup_failure_still_closes_resources(self):
        events = []

        async def ok():
            events.append("initialize")

        async def fail():
            raise RuntimeError("restore failed")

        async def close():
            events.append("close")

        with self.assertRaises(RuntimeError):
            async with chat_only_lifespan(initialize=ok, restore=fail, close=close):
                self.fail("must not serve after failed initialization")
        self.assertEqual(events, ["initialize", "close"])

    def test_worker_opt_in_is_explicit(self):
        for value in ("", "0", "true", "yes", "1 "):
            with self.subTest(value=value), patch.dict(
                os.environ, {"SHENXIAO_ENABLE_UPSTREAM_RUNTIME": value}, clear=True
            ):
                self.assertFalse(upstream_runtime_enabled())
        with patch.dict(os.environ, {"SHENXIAO_ENABLE_UPSTREAM_RUNTIME": "1"}, clear=True):
            self.assertTrue(upstream_runtime_enabled())


class AndroidBoundaryTests(unittest.TestCase):
    def test_packaged_entry_cannot_start_legacy_components_or_request_sensors(self):
        manifest = ET.parse(ROOT / "AionApp/app/src/main/AndroidManifest.xml").getroot()
        permissions = {node.get(ANDROID + "name") for node in manifest.findall("uses-permission")}
        self.assertEqual(permissions, {"android.permission.INTERNET",
                                       "android.permission.ACCESS_NETWORK_STATE"})
        app = manifest.find("application")
        self.assertEqual(app.get(ANDROID + "allowBackup"), "false")
        self.assertEqual([node.tag for node in app], ["activity"])
        self.assertEqual(app[0].get(ANDROID + "name"), ".ShenXiaoActivity")

    @unittest.skipUnless(shutil.which("java"), "JDK required")
    def test_real_java_url_policy_rejects_external_and_credential_urls(self):
        source = ROOT / "AionApp/app/src/main/java/com/aion/chat/ShenXiaoEndpoint.java"
        harness = r'''
package com.aion.chat;
public class EndpointCheck {
    public static void main(String[] args) {
        String[] allowed = {"http://100.64.0.1:8080", "http://100.127.255.254:8080/chat",
            "http://192.168.1.2/", "http://172.16.0.1", "https://host.tail123.ts.net",
            "http://localhost:8080", "http://[::1]:8080", "http://10.0.0.1"};
        String[] denied = {"https://example.com", "http://100.63.255.255", "http://100.128.0.1",
            "http://172.32.0.1", "file:///etc/passwd", "javascript:alert(1)",
            "http://name:secret@100.64.0.1", "http://100.64.0.1?token=secret",
            "http://100.64.0.1/#token", "http://100.64.0.1:0", "http://100.64.0.1:65536",
            "http://192.168.1.999", "http://192.168.01.1", "http://host.ts.net.evil.com",
            "http://192.168.1.2/private", "http://127.1", "http://2130706433"};
        for (String value : allowed) {
            if (ShenXiaoEndpoint.normalize(value) == null) throw new AssertionError(value);
        }
        for (String value : denied) {
            if (ShenXiaoEndpoint.normalize(value) != null) throw new AssertionError(value);
        }
        String base = "http://100.64.0.1:8080/chat";
        if (!ShenXiaoEndpoint.sameOrigin(base, "http://100.64.0.1:8080/settings"))
            throw new AssertionError("same origin rejected");
        String[] cross = {"http://100.64.0.1:8081/chat", "https://100.64.0.1:8080/chat",
            "http://evil.com/chat", "file:///etc/passwd", "http://me@100.64.0.1:8080/chat"};
        for (String value : cross) {
            if (ShenXiaoEndpoint.sameOrigin(base, value)) throw new AssertionError(value);
        }
        if (!ShenXiaoEndpoint.sameOrigin("https://host.ts.net/chat", "https://host.ts.net:443/"))
            throw new AssertionError("default port mismatch");
    }
}'''
        with tempfile.TemporaryDirectory() as tmp:
            runner = Path(tmp) / "EndpointCheck.java"
            runner.write_text(harness, encoding="utf-8")
            compiler = ["javac"] if shutil.which("javac") else [
                "java", "--module", "jdk.compiler/com.sun.tools.javac.Main"]
            subprocess.run(compiler + ["-d", tmp, str(source), str(runner)], check=True, timeout=30)
            subprocess.run(["java", "-cp", tmp, "com.aion.chat.EndpointCheck"], check=True, timeout=30)


if __name__ == "__main__":
    unittest.main()
