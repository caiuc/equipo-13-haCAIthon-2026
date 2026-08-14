import numpy as np
from ia.modelos.agent_group import AgentGroup


class Encoder:
    def __init__(self,size): self.size=size
class Phase: pass
class Logic:
    def __init__(self,n): self.phases=[Phase() for _ in range(n)]
class Env:
    encoders={'a':Encoder(3),'b':Encoder(5)}


def cfg():
    return {'rl':{
        'agent_architecture':'shared','learning_rate':0.001,'replay_capacity':100,
        'epsilon_start':0.0,'epsilon_end':0.0,'epsilon_decay_steps':10,'gamma':0.99,
        'batch_size':2,'target_update_steps':10,'hidden_units':[16,16],'gradient_clip':10.0
    }}


def test_shared_agent_pads_states_and_masks_actions():
    logic={'a':Logic(2),'b':Logic(4)}
    g=AgentGroup(Env(),logic,cfg(),seed=1)
    obs={'a':np.zeros(3,dtype=np.float32),'b':np.zeros(5,dtype=np.float32)}
    masks={'a':[True,False],'b':[False,False,True,False]}
    actions=g.select_actions(obs,masks,training=False)
    assert actions['a']==0
    assert actions['b']==2
