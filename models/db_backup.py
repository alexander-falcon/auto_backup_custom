# -*- coding: utf-8 -*-

import logging
import os
import shutil
import traceback
from contextlib import contextmanager
from datetime import datetime, timedelta
from glob import iglob

import pysftp

from odoo import _, api, exceptions, fields, models, tools
from odoo.exceptions import UserError
from odoo.service import db

_logger = logging.getLogger(__name__)

class DbBackupCustom(models.Model):
    _inherit = 'db.backup'

    def action_backup(self):
        """Run selected backups."""
        backup = None
        successful = self.browse()

        # Start with local storage
        for rec in self.filtered(lambda r: r.method == "local"):
            filename = self.filename(datetime.now(), ext=rec.backup_format)
            with rec.backup_log():
                # Directory must exist
                try:
                    os.makedirs(rec.folder)
                except OSError as exc:
                    _logger.exception("Action backup - OSError: %s" % exc)

                with open(os.path.join(rec.folder, filename), "wb") as destiny:
                    # Copy the cached backup
                    if backup:
                        with open(backup) as cached:
                            shutil.copyfileobj(cached, destiny)
                    # Generate new backup
                    else:
                        db.dump_db(
                            self.env.cr.dbname, destiny, backup_format=rec.backup_format
                        )
                        backup = backup or destiny.name
                successful |= rec

        # Ensure a local backup exists if we are going to write it remotely
        sftp = self.filtered(lambda r: r.method == "sftp")
        if sftp:
            for rec in sftp:
                filename = self.filename(datetime.now(), ext=rec.backup_format)
                with rec.backup_log():

                    cached = db.dump_db(
                        self.env.cr.dbname, None, backup_format=rec.backup_format
                    )

                    with cached:
                        with rec.sftp_connection() as remote:
                            # Directory must exist
                            try:
                                remote.makedirs(rec.folder)
                            except pysftp.ConnectionException as exc:
                                _logger.exception(
                                    "pysftp ConnectionException: %s" % exc
                                )

                            # Copy cached backup to remote server
                            with remote.open(
                                os.path.join(rec.folder, filename), "wb"
                            ) as destiny:
                                shutil.copyfileobj(cached, destiny)
                        successful |= rec

        # Remove old files for successful backups
        successful.cleanup()

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
