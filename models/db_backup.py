# -*- coding: utf-8 -*-

from odoo import models
import logging
import pysftp

_logger = logging.getLogger(__name__)

class DbBackupCustom(models.Model):
    _inherit = 'db.backup'

    def sftp_connection(self):
        """Return a new SFTP connection with found parameters."""
        self.ensure_one()
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None
        params = {
            "host": self.sftp_host,
            "username": self.sftp_user,
            "port": self.sftp_port,
            "cnopts": cnopts  
        }
        _logger.debug(
            "Trying to connect to sftp://%(username)s@%(host)s:%(port)d", extra=params
        )
        if self.sftp_private_key:
            params["private_key"] = self.sftp_private_key
            if self.sftp_password:
                params["private_key_pass"] = self.sftp_password
        else:
            params["password"] = self.sftp_password

        return pysftp.Connection(**params)
