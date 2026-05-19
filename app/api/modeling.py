import torch
from torch import nn
from transformers import RobertaModel, RobertaPreTrainedModel
from transformers.modeling_outputs import SequenceClassifierOutput


class CoAttention(nn.Module):
    def __init__(self, hidden_size):
        super().__init__()
        self.W = nn.Linear(hidden_size, hidden_size, bias=False)

    def forward(self, title_hidden, lead_hidden, title_mask, lead_mask):
        proj_lead = self.W(lead_hidden)
        scores = torch.bmm(title_hidden, proj_lead.transpose(1, 2))

        scores_t2l = scores.masked_fill(lead_mask.unsqueeze(1) == 0, float("-inf"))
        alpha_t2l = torch.softmax(scores_t2l, dim=2)
        alpha_t2l = alpha_t2l.masked_fill(torch.isnan(alpha_t2l), 0.0)
        c_title = torch.bmm(alpha_t2l, lead_hidden)

        scores_l2t = scores.transpose(1, 2).masked_fill(title_mask.unsqueeze(1) == 0, float("-inf"))
        alpha_l2t = torch.softmax(scores_l2t, dim=2)
        alpha_l2t = alpha_l2t.masked_fill(torch.isnan(alpha_l2t), 0.0)
        c_lead = torch.bmm(alpha_l2t, title_hidden)

        return c_title, c_lead


class AttentionPooling(nn.Module):
    def __init__(self, hidden_size):
        super().__init__()
        self.attention = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.Tanh(),
            nn.Linear(hidden_size, 1),
        )

    def forward(self, hidden_states, attention_mask):
        weights = self.attention(hidden_states)
        mask = attention_mask.unsqueeze(-1)
        weights = weights.masked_fill(mask == 0, float("-inf"))
        alpha = torch.softmax(weights, dim=1)
        alpha = alpha.masked_fill(torch.isnan(alpha), 0.0)
        return torch.sum(alpha * hidden_states, dim=1)


class PhoBertWithCoAttentionPooling(RobertaPreTrainedModel):
    def __init__(self, config):
        super().__init__(config)
        self.num_labels = config.num_labels
        self.config = config

        self.roberta = RobertaModel(config, add_pooling_layer=False)
        self.co_attention = CoAttention(config.hidden_size)
        self.pooler_title = AttentionPooling(config.hidden_size)
        self.pooler_lead = AttentionPooling(config.hidden_size)
        self.classifier = nn.Sequential(
            nn.Dropout(config.hidden_dropout_prob),
            nn.Linear(config.hidden_size * 4, config.hidden_size),
            nn.Tanh(),
            nn.Dropout(config.hidden_dropout_prob),
            nn.Linear(config.hidden_size, config.num_labels),
        )

        self.post_init()

    def forward(
        self,
        input_ids=None,
        attention_mask=None,
        token_type_ids=None,
        position_ids=None,
        head_mask=None,
        inputs_embeds=None,
        labels=None,
        output_attentions=None,
        output_hidden_states=None,
        return_dict=None,
    ):
        return_dict = return_dict if return_dict is not None else self.config.use_return_dict

        outputs = self.roberta(
            input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
            position_ids=position_ids,
            head_mask=head_mask,
            inputs_embeds=inputs_embeds,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            return_dict=return_dict,
        )
        hidden_states = outputs[0]

        sep_id = self.config.eos_token_id if self.config.eos_token_id is not None else 2
        cls_id = self.config.bos_token_id if self.config.bos_token_id is not None else 0
        sep_cumsum = (input_ids == sep_id).cumsum(dim=1)

        title_mask = (sep_cumsum == 0) & (input_ids != cls_id) & (attention_mask == 1)
        lead_mask = (sep_cumsum == 2) & (input_ids != sep_id) & (attention_mask == 1)

        c_title, c_lead = self.co_attention(hidden_states, hidden_states, title_mask, lead_mask)
        enhanced_title = hidden_states + c_title
        enhanced_lead = hidden_states + c_lead

        u_title = self.pooler_title(enhanced_title, title_mask)
        u_lead = self.pooler_lead(enhanced_lead, lead_mask)
        diff = torch.abs(u_title - u_lead)
        prod = u_title * u_lead
        logits = self.classifier(torch.cat([u_title, u_lead, diff, prod], dim=-1))

        loss = None
        if labels is not None:
            loss = nn.CrossEntropyLoss()(logits.view(-1, self.num_labels), labels.view(-1))

        if not return_dict:
            output = (logits,) + outputs[2:]
            return ((loss,) + output) if loss is not None else output

        return SequenceClassifierOutput(
            loss=loss,
            logits=logits,
            hidden_states=outputs.hidden_states,
            attentions=outputs.attentions,
        )
