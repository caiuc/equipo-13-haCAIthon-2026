from ia.entrenamiento.train import train
from ia.modelos.agent_group import AgentGroup
from simulacion.trafico.multi_agent_environment import MultiAgentTrafficEnv


def test_dqn_trains_saves_and_loads_same_environment(fast_cfg, logic, tmp_path):
    result = train(fast_cfg, logic, episodes=2, seconds=30, out_dir=tmp_path)
    assert (tmp_path / "i1.pt").is_file()
    assert (tmp_path / "i2.pt").is_file()
    assert any(any(value > 0 for value in row["loss"].values()) for row in result["history"])

    env = MultiAgentTrafficEnv(fast_cfg, logic, episode_seconds=20, seed=99)
    group = AgentGroup(env, logic, fast_cfg, seed=99)
    assert group.load(tmp_path)
    observations = env.reset(seed=99)
    actions = group.select_actions(observations, env.action_masks(), training=False)
    assert set(actions) == {"i1", "i2"}
    assert all(env.action_masks()[iid][action] for iid, action in actions.items())
