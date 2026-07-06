"""Comprehensive Phase 3 verification test."""

import asyncio


async def test_phase3_complete():
    """Verify all Phase 3 requirements are met."""

    print('=== Phase 3: Environment Awareness - Verification ===\n')

    # 1. EnvironmentState structure
    from core.environment import EnvironmentState
    from datetime import datetime

    # Check all required fields
    test_env = EnvironmentState(
        cwd='.',
        workspace={},
        computer={},
        network={},
        developer={},
        operating_system={},
        observed_at=datetime.now()
    )
    assert hasattr(test_env, 'observed_at'), 'Missing observed_at field'
    print('✓ EnvironmentState has all required fields including observed_at')

    # 2. All five observers exist and return dicts
    from observers import workspace, network, computer, developer, os as os_observer

    ws = await workspace.inspect('.')
    assert isinstance(ws, dict), 'workspace.inspect must return dict'
    print('✓ workspace observer returns dict')

    net = await network.inspect('.')
    assert isinstance(net, dict), 'network.inspect must return dict'
    print('✓ network observer returns dict')

    comp = await computer.inspect('.')
    assert isinstance(comp, dict), 'computer.inspect must return dict'
    print('✓ computer observer returns dict')

    dev = await developer.inspect('.')
    assert isinstance(dev, dict), 'developer.inspect must return dict'
    print('✓ developer observer returns dict')

    os_data = await os_observer.inspect('.')
    assert isinstance(os_data, dict), 'os.inspect must return dict'
    print('✓ os observer returns dict')

    # 3. Secret redaction
    from observers.os import _should_redact

    assert _should_redact('API_KEY') == True
    assert _should_redact('SECRET_TOKEN') == True
    assert _should_redact('PASSWORD') == True
    assert _should_redact('USER') == False
    assert _should_redact('PATH') == False
    print('✓ Secret redaction working')

    # 4. Environment manager with caching
    from core.environment_manager import inspect_environment, _cache
    import time

    # Clear cache first
    _cache['computer'] = None
    _cache['developer'] = None
    _cache['os'] = None

    start = time.time()
    env1 = await inspect_environment(cwd='.')
    time1 = time.time() - start

    start = time.time()
    env2 = await inspect_environment(cwd='.')
    time2 = time.time() - start

    speedup = time1 / time2 if time2 > 0 else 0
    assert speedup > 2, f'Cache should provide speedup, got {speedup}x'
    print(f'✓ Cache provides {speedup:.1f}x speedup on second call')

    # 5. PipelineRun has environment field
    from core.run import PipelineRun
    from core.intent import Intent

    intent = Intent(payload={'text': 'test'})
    run = PipelineRun(intent=intent)
    assert hasattr(run, 'environment'), 'PipelineRun missing environment field'
    print('✓ PipelineRun has environment field')

    # 6. Planner receives environment
    from agents.planner import create_plan
    from dataclasses import asdict
    import json

    # Just verify planner can be called with environment
    # (don't actually call the model)
    import agents.planner as planner_module
    original = planner_module.call_model

    captured_prompt = None
    async def capture(prompt):
        nonlocal captured_prompt
        captured_prompt = prompt
        return json.dumps([])

    planner_module.call_model = capture
    await create_plan('test', env1, '')
    planner_module.call_model = original

    assert 'Environment:' in captured_prompt, 'Environment not in prompt'
    assert '"workspace":' in captured_prompt, 'workspace data missing'
    assert '"computer":' in captured_prompt, 'computer data missing'
    print('✓ Planner receives environment in prompt')

    print('\n=== All Phase 3 Requirements Verified ===')


if __name__ == '__main__':
    asyncio.run(test_phase3_complete())
