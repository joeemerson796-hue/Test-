# -*- coding: utf-8 -*-
from odoo import fields, models


class HelpdeskTicketProductLine(models.Model):
    _name = 'helpdesk.ticket.product.line'
    _description = 'Helpdesk Ticket Product Line'

    ticket_id = fields.Many2one(
        'helpdesk.ticket',
        required=True,
        ondelete='cascade',
        string='Ticket',
    )
    product_id = fields.Many2one(
        'product.product',
        required=True,
        string='Product',
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='UOM',
    )
    demand = fields.Float(
        string='Demand',
        default=0.0,
    )
    quantity = fields.Float(
        string='Quantity',
        default=0.0,
    )
    color = fields.Char(
        string='اللون',
    )
    shipping_notes = fields.Char(
        string='ملاحظات فريق الشحن',
    )
    is_checked = fields.Boolean(
        string='Checked',
        default=False,
    )
    receipt_done = fields.Boolean(
        string='Receipt Done',
        default=False,
        copy=False,
    )
