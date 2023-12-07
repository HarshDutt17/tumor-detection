import torch
import torch.nn as nn
from torch.nn import Parameter
import torch.nn.functional as F
from networks.segtran_shared import CrossAttFeatTrans, SegtranInitWeights, SegtranConfig
torch.set_printoptions(sci_mode=False)

class PolyformerLayer(SegtranInitWeights):
    def __init__(self, name, config):
        super(PolyformerLayer, self).__init__(config)
        self.name           = name
        self.chan_axis      = config.chan_axis
        self.feat_dim       = config.feat_dim
        self.num_attractors = config.num_attractors
        self.qk_have_bias   = config.qk_have_bias
        # If disabling multi-mode expansion in in_ator_trans, performance will drop 1-2%.
        # config1.num_modes = 1
        self.in_ator_trans  = CrossAttFeatTrans(config, name + '-in-squeeze')
        self.ator_out_trans = CrossAttFeatTrans(config, name + '-squeeze-out')
        self.attractors     = Parameter(torch.randn(1, self.num_attractors, self.feat_dim))
        self.infeat_norm_layer = nn.LayerNorm(self.feat_dim, eps=1e-12, elementwise_affine=False)
        self.poly_do_layernorm = config.poly_do_layernorm
        print("Polyformer layer {}: {} attractors, {} modes, {} channels, {} layernorm".format(
                    name, self.num_attractors, config.num_modes, self.feat_dim, 
                    'with' if self.poly_do_layernorm else 'no'))
        
        self.pool2x = nn.AvgPool2d(2)
        self.apply(self.init_weights)
        # tie_qk() has to be executed after weight initialization.
        # tie_qk() of in_ator_trans and ator_out_trans are executed.
        self.apply(self.tie_qk)
        self.apply(self.add_identity_bias)
                
    def forward(self, in_feat):
        B           = in_feat.shape[0]
        # in_feat is 288x288. Full computation for transformers is a bit slow. 
        # So downsample it by 2x. The performance is almost the same.
        in_feat_half0 = self.pool2x(in_feat)
        in_feat_half  = in_feat_half0.transpose(self.chan_axis, -1)
        # Using layernorm reduces performance by 1-2%. Maybe because in_feat has just passed through ReLU(),
        # and a naive layernorm makes zero activations non-zero.
        if self.poly_do_layernorm:
            in_feat_half    = self.infeat_norm_layer(in_feat_half)
        vfeat   = in_feat_half.reshape((B, -1, self.feat_dim))
        
        batch_attractors     = self.attractors.expand(B, -1, -1)
        new_batch_attractors = self.in_ator_trans(batch_attractors, vfeat)
        vfeat_out = self.ator_out_trans(vfeat, new_batch_attractors)
        vfeat_out = vfeat_out.transpose(self.chan_axis, -1)
        out_feat_half   = vfeat_out.reshape(in_feat_half0.shape)
        out_feat = F.interpolate(out_feat_half, size=in_feat.shape[2:],
                                 mode='bilinear', align_corners=False)
        out_feat = in_feat + out_feat
            
        return out_feat

class Polyformer(nn.Module):
    def __init__(self, feat_dim, chan_axis=1, args=None):
        config = SegtranConfig()
        if args is None:
            config.num_attractors       = 256
            config.num_modes            = 4
            config.tie_qk_scheme        = 'loose'
            config.qk_have_bias         = True
            config.pos_code_type        = 'lsinu'
        else:
            config.num_attractors       = args.num_attractors
            if args.num_modes != -1:
                config.num_modes        = args.num_modes
            else:
                config.num_modes        = 4
            config.tie_qk_scheme        = args.tie_qk_scheme    # shared, loose, or none.
            config.qk_have_bias         = args.qk_have_bias
            config.pos_code_type        = args.pos_code_type
        
        config.num_layers   = 1 
        config.in_feat_dim  = feat_dim
        config.feat_dim     = feat_dim
        config.min_feat_dim = feat_dim

        # Removing biases from V seems to slightly improve performance.
        config.v_has_bias       = False
        # has_FFN is False: Only aggregate features, not transform them with an FFN. 
        # In the old setting, has_FFN is implicitly True. 
        # To reproduce paper results, please set it to True.
        config.has_FFN          = False
        config.ablate_multihead = False
        config.chan_axis            = chan_axis

        config.poly_do_layernorm    = False

        super(Polyformer, self).__init__()
        
        polyformer_layers = []
        for i in range(config.num_layers):
            if i > 0:
                config.only_first_linear = False
            polyformer_layers.append( PolyformerLayer(str(i), config) )
        self.polyformer_layers = nn.Sequential(*polyformer_layers)
        
    def forward(self, in_feat):
        out_feat = self.polyformer_layers(in_feat)
        return out_feat
        