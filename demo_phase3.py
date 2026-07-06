"""Demonstration of Phase 3 verbose output in action."""

import asyncio
import os

# Enable verbose pipeline output
os.environ['VERBOSE_PIPELINE'] = '1'


async def demo_verbose_output():
    """Demonstrate verbose environment output as it appears in the pipeline."""

    from core.environment_manager import inspect_environment
    from core.pipeline import _format_environment_verbose

    print('=== Phase 3: Verbose Output Demo ===\n')

    # Inspect environment
    env = await inspect_environment(cwd='.')

    # Format and display (this is what users see when VERBOSE_PIPELINE=1)
    _format_environment_verbose(env)

    print('[INFO] Environment inspection complete')
    print(f'[INFO] Collected data from {len([env.workspace, env.computer, env.network, env.developer, env.operating_system])} observer categories')
    print(f'[INFO] Cache TTL: 5 minutes for near-static data')
    print(f'[INFO] Observed at: {env.observed_at.strftime("%Y-%m-%d %H:%M:%S")}')


if __name__ == '__main__':
    asyncio.run(demo_verbose_output())
