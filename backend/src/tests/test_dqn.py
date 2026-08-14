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
