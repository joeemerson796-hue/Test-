# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    ticket_product_line_ids = fields.One2many(
        'helpdesk.ticket.product.line',
        'ticket_id',
        string='Product Lines',
    )
    policy_number = fields.Char(string="رقم البوليصة")
    shipping_policy_company = fields.Selection(
        [
            ('smsa', 'SMSA'),
            ('aramex', 'Aramex'),
        ],
        string="Shipping Policy Company",
    )
    smsa_url = fields.Char(string="SMSA URL")
    aramex_url = fields.Char(string="Aramex URL")
    label_file = fields.Binary(string="Label File", attachment=True)
    label_file_name = fields.Char()
    file_link = fields.Char(string="File Link")
    product_condition = fields.Selection(
        [
            ('excellent', 'Excellent'),
            ('good', 'Good'),
            ('acceptable', 'Acceptable'),
            ('damaged', 'Damaged'),
        ],
        string="Product Condition",
        tracking=True,
    )
    damage_description = fields.Text(
        string="Damage / Issue Description",
        tracking=True,
    )

    has_unprocessed_checked = fields.Boolean(
        compute='_compute_has_unprocessed_checked',
    )

    def _refresh_file_link(self):
        """Look up the standard attachment for label_file and write file_link."""
        self.ensure_one()
        if not isinstance(self.id, int):
            return False
        if not self.label_file:
            super(HelpdeskTicket, self).write({'file_link': False})
            return False
        attachment = self.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'helpdesk.ticket'),
            ('res_id', '=', self.id),
            ('res_field', '=', 'label_file'),
        ], limit=1)
        if not attachment:
            super(HelpdeskTicket, self).write({'file_link': False})
            return False
        if not attachment.public:
            attachment.sudo().write({'public': True})
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or ''
        url = '%s/web/content/%s' % (base_url, attachment.id)
        if self.file_link != url:
            super(HelpdeskTicket, self).write({'file_link': url})
        return url

    @api.onchange('label_file', 'label_file_name')
    def _onchange_label_file(self):
        origin = self._origin
        # New, unsaved ticket: link will appear after first save (handled in create)
        if not isinstance(origin.id, int):
            return
        # Persist the upload immediately so the standard attachment is created now
        origin.write({
            'label_file': self.label_file,
            'label_file_name': self.label_file_name,
        })
        url = origin._refresh_file_link()
        self.file_link = url or False

    def write(self, vals):
        res = super().write(vals)
        if 'label_file' in vals or 'label_file_name' in vals:
            for rec in self:
                rec._refresh_file_link()
        return res

    @api.depends(
        'ticket_product_line_ids.is_checked',
        'ticket_product_line_ids.receipt_done',
    )
    def _compute_has_unprocessed_checked(self):
        for ticket in self:
            ticket.has_unprocessed_checked = any(
                line.is_checked and not line.receipt_done
                for line in ticket.ticket_product_line_ids
            )

    @api.model
    def create(self, vals):
        ticket = super().create(vals)
        sale_order = getattr(ticket, 'sale_order_id', False)
        if sale_order:
            ProductLine = self.env['helpdesk.ticket.product.line']
            for line in sale_order.order_line:
                ProductLine.create({
                    'ticket_id': ticket.id,
                    'product_id': line.product_id.id,
                    'uom_id': line.product_uom.id,
                    'demand': line.product_uom_qty,
                    'quantity': 0.0,
                })
        if ticket.label_file:
            ticket._refresh_file_link()
        return ticket

    def action_create_receipt(self):
        self.ensure_one()
        checked_lines = self.ticket_product_line_ids.filtered(
            lambda l: l.is_checked and not l.receipt_done
        )
        if not checked_lines:
            raise UserError(_("Please check at least one unprocessed product line."))
        if not self.sale_order_id:
            raise UserError(_("This ticket is not linked to a Sale Order."))

        out_pickings = self.sale_order_id.picking_ids.filtered(
            lambda p: p.picking_type_id.code == 'outgoing'
        ).sorted('id')
        if not out_pickings:
            raise UserError(_(
                "The related Sale Order does not have a Delivery Order (WH/OUT)."
            ))
        picking = out_pickings[-1]

        # Map original delivered/demanded qty per product on the WH/OUT
        qty_map = {}
        for move in picking.move_ids:
            qty_map.setdefault(move.product_id.id, 0.0)
            qty_map[move.product_id.id] += move.product_uom_qty

        # Create the return picking directly (Odoo 17 compatible — no wizard)
        return_type = picking.picking_type_id.return_picking_type_id or picking.picking_type_id
        return_picking = picking.copy({
            'origin': _('Return of %s') % picking.name,
            'picking_type_id': return_type.id,
            'location_id': picking.location_dest_id.id,
            'location_dest_id': picking.location_id.id,
            'move_ids': [],
        })

        # For each checked line: copy the matching source move onto the return,
        # then mirror its move-line lots/qties so validation happens silently.
        new_moves_by_src = {}
        for line in checked_lines:
            src_move = picking.move_ids.filtered(
                lambda m: m.product_id.id == line.product_id.id
            )[:1]
            if not src_move:
                continue
            new_move = src_move.copy({
                'picking_id': return_picking.id,
                'product_uom_qty': src_move.product_uom_qty,
                'location_id': picking.location_dest_id.id,
                'location_dest_id': picking.location_id.id,
                'origin_returned_move_id': src_move.id,
                'move_orig_ids': False,
                'move_dest_ids': False,
                'move_line_ids': [],
            })
            new_moves_by_src[src_move.id] = new_move

        if not new_moves_by_src:
            raise UserError(_(
                "None of the checked products are available on the related WH/OUT picking."
            ))

        return_picking.with_context(skip_backorder=True).action_confirm()

        # Wipe any auto-created move lines on the return moves, then mirror
        # the original WH/OUT move lines (lots/serials) onto the return moves.
        for new_move in new_moves_by_src.values():
            new_move.move_line_ids.unlink()

        for return_move in new_moves_by_src.values():
            for orig_move in picking.move_ids:
                if orig_move.product_id == return_move.product_id:
                    for orig_line in orig_move.move_line_ids:
                        return_move.move_line_ids.create({
                            'move_id': return_move.id,
                            'picking_id': return_picking.id,
                            'product_id': orig_line.product_id.id,
                            'product_uom_id': orig_line.product_uom_id.id,
                            'quantity': orig_line.quantity,
                            'lot_id': orig_line.lot_id.id if orig_line.lot_id else False,
                            'location_id': return_picking.location_id.id,
                            'location_dest_id': return_picking.location_dest_id.id,
                        })
            if not return_move.move_line_ids:
                # Fallback if the source picking had no move lines yet
                return_move.quantity = return_move.product_uom_qty
            if 'picked' in return_move._fields:
                return_move.picked = True

        # Validate silently — skip_backorder drops any unfilled qty, no popup
        return_picking.with_context(
            skip_backorder=True,
            picking_ids_not_to_backorder=return_picking.ids,
        ).button_validate()

        # Write the original delivered qty back into each line and lock it
        processed_count = 0
        for line in checked_lines:
            if line.product_id.id in {
                self.env['stock.move'].browse(sid).product_id.id for sid in new_moves_by_src
            }:
                line.quantity = qty_map.get(line.product_id.id, line.quantity)
                line.receipt_done = True
                line.is_checked = False
                processed_count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Receipt"),
                'message': _("Return %s validated. %s line(s) processed.") % (
                    return_picking.name, processed_count,
                ),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
