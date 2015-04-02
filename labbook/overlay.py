#!/usr/bin/python2
# -*- coding: utf-8 -*-

__all__ = ['mount']


from __future__ import with_statement

import os
import sys
import errno

from fuse import FUSE, FuseOSError, Operations

class Overlay(Operations):
    def __init__(self, mount, root, overlay):
        self.mount = mount
        self.root = root
        self.overlay = overlay

    # Helpers
    # =======

    def _read_path(self, path):
        if path.startswith("/"):
            path = path[1:]

        if os.path.exists(os.path.join(self.overlay, path)):
            return os.path.join(self.overlay, path)
        else:
            return os.path.join(self.root, path)

    def _write_path(self, path):
        if path.startswith("/"):
            path = path[1:]
        return os.path.join(self.overlay, path)

    # Filesystem methods
    # ==================

    def access(self, path, mode):
        full_path = self._read_path(path)
        if not os.access(full_path, mode):
            raise FuseOSError(errno.EACCES)

    def chmod(self, path, mode):
        full_path = self._write_path(path)
        return os.chmod(full_path, mode)

    def chown(self, path, uid, gid):
        full_path = self._write_path(path)
        return os.chown(full_path, uid, gid)

    def getattr(self, path, fh=None):
        full_path = self._read_path(path)
        st = os.lstat(full_path)
        return dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
                     'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid'))

    def readdir(self, path, fh):
        full_path = self._read_path(path)

        dirents = ['.', '..']
        if os.path.isdir(full_path):
            dirents.extend(os.listdir(full_path))
        for r in dirents:
            yield r

    def readlink(self, path):
        pathname = os.readlink(self._read_path(path))
        if pathname.startswith("/"):
            # Path name is absolute, sanitize it.
            return os.path.relpath(pathname, self.root)
        else:
            return pathname

    def mknod(self, path, mode, dev):
        return os.mknod(self._write_path(path), mode, dev)

    def rmdir(self, path):
        full_path = self._write_path(path)
        return os.rmdir(full_path)

    def mkdir(self, path, mode):
        return os.mkdir(self._write_path(path), mode)

    def statfs(self, path):
        full_path = self._read_path(path)
        stv = os.statvfs(full_path)
        return dict((key, getattr(stv, key)) for key in ('f_bavail', 'f_bfree',
            'f_blocks', 'f_bsize', 'f_favail', 'f_ffree', 'f_files', 'f_flag',
            'f_frsize', 'f_namemax'))

    def unlink(self, path):
        return os.unlink(self._write_path(path))

    def symlink(self, name, target):
        return os.symlink(name, self._write_path(target))

    def rename(self, old, new):
        return os.rename(self._write_path(old), self._write_path(new))

    def link(self, target, name):
        return os.link(self._write_path(target), self._write_path(name))

    def utimens(self, path, times=None):
        return os.utime(self._read_path(path), times)

    # File methods
    # ============

    def open(self, path, flags):
        if (os.O_RDWR & flags) or (os.O_WRONLY & flags):
            full_path = self._write_path(path)
            if not os.path.exists(full_path):
                os.open(full_path, os.O_WRONLY | os.O_CREAT)
        else:
            full_path = self._read_path(path)
        return os.open(full_path, flags)

    def create(self, path, mode, fi=None):
        full_path = self._write_path(path)
        return os.open(full_path, os.O_WRONLY | os.O_CREAT, mode)

    def read(self, path, length, offset, fh):
        os.lseek(fh, offset, os.SEEK_SET)
        return os.read(fh, length)

    def write(self, path, buf, offset, fh):
        os.lseek(fh, offset, os.SEEK_SET)
        return os.write(fh, buf)

    def truncate(self, path, length, fh=None):
        full_path = self._write_path(path)
        with open(full_path, 'r+') as f:
            f.truncate(length)

    def flush(self, path, fh):
        return os.fsync(fh)

    def release(self, path, fh):
        return os.close(fh)

    def fsync(self, path, fdatasync, fh):
        return self.flush(path, fh)


def mount(mountpoint, root, overlay):
    FUSE(Overlay(mountpoint, root, overlay), mountpoint, foreground=True)

if __name__ == '__main__':
    mount(sys.argv[3], sys.argv[1], sys.argv[2])
