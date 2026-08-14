import numpy as np
from ia.modelos.dqn import DQNAgent

CFG={
 'learning_rate':0.001,'replay_capacity':100,'epsilon_start':0.0,'epsilon_end':0.0,
 'epsilon_decay_steps':10,'gamma':0.99,'batch_size':2,'target_update_steps':10,
 'hidden_units':[16,16],'gradient_clip':10.0
}

def test_action_mask_never_selects_invalid_action():
    a=DQNAgent(4,3,CFG,device='cpu')
    state=np.zeros(4,dtype=np.float32)
    for _ in range(5):
        assert a.select_action(state,[False,True,False],training=False)==1


def test_epsilon_never_below_end():
    cfg=dict(CFG); cfg['epsilon_start']=1.0; cfg['epsilon_end']=0.05; cfg['epsilon_decay_steps']=5; cfg['epsilon_warmup_steps']=0
    a=DQNAgent(4,3,cfg,device='cpu')
    a.steps=10_000
    assert abs(a.epsilon-cfg['epsilon_end'])<1e-9


def test_epsilon_holds_start_value_during_warmup():
    cfg=dict(CFG); cfg['epsilon_start']=1.0; cfg['epsilon_end']=0.05; cfg['epsilon_decay_steps']=100; cfg['epsilon_warmup_steps']=50
    a=DQNAgent(4,3,cfg,device='cpu')
    a.steps=10
    assert a.epsilon==cfg['epsilon_start']
    a.steps=51
    assert a.epsilon < cfg['epsilon_start']


def test_learning_starts_gate_blocks_gradient_updates():
    cfg=dict(CFG); cfg['learning_starts_steps']=5; cfg['batch_size']=1
    a=DQNAgent(2,2,cfg,device='cpu')
    state=np.zeros(2,dtype=np.float32)
    for _ in range(4):
        a.remember(state,0,1.0,state,False,[True,True])
    assert a.steps==4
    assert a.learn() is None
    a.remember(state,0,1.0,state,False,[True,True])
    assert a.steps==5
    assert a.learn() is not None
