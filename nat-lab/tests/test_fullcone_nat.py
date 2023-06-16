from utils.asyncio_util import run_async_context
from contextlib import AsyncExitStack
from utils import ConnectionTag, new_connection_by_tag
import asyncio
import pytest

TESTING_STRING = "test failed"
LOCAL_PORT = 1235
LOCAL_IP = "10.0.254.4"


@pytest.mark.nat
@pytest.mark.asyncio
async def test_fullcone_nat() -> None:
    async with AsyncExitStack() as exit_stack:
        connection_1 = await exit_stack.enter_async_context(
            new_connection_by_tag(ConnectionTag.DOCKER_FULLCONE_CLIENT_1)
        )

        connection_2 = await exit_stack.enter_async_context(
            new_connection_by_tag(ConnectionTag.DOCKER_CONE_CLIENT_1)
        )

        # listen for udp packets on connection1 local port
        event = asyncio.Event()
        listening_process = connection_1.create_process(
            ["nc", "-n", "-l", "-u", "-v", "-p", str(LOCAL_PORT)]
        )

        async def on_stdout(stdout: str) -> None:
            print(stdout)
            if TESTING_STRING in stdout:
                event.set()

        await exit_stack.enter_async_context(
            run_async_context(listening_process.execute(stdout_callback=on_stdout))
        )

        await listening_process.wait_stdin_ready()

        # send udp packet from connection2 to connection1 to its external ip
        send_process = connection_2.create_process(
            ["nc", "-n", "-u", "-v", LOCAL_IP, str(LOCAL_PORT)]
        )

        await exit_stack.enter_async_context(run_async_context(send_process.execute()))
        await send_process.wait_stdin_ready()
        await asyncio.sleep(1)
        await send_process.write_stdin(TESTING_STRING)

        await asyncio.sleep(2)

        assert len(listening_process.get_stdout()) == 0
