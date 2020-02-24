from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client, get_tracker_conf
from django.conf import settings


class FDFSStorage(Storage):
    """fast DFS文件存储类"""

    def __init__(self, client_conf=None, base_url=None):
        """初始化"""
        if not client_conf:
            client_conf = settings.FDFS_CLIENT_CONF
        self.client_conf = client_conf

        if not base_url:
            base_url = settings.FDFS_URL
        self.base_url = base_url

    def open(self, name, mode='rb'):
        """打开文件时使用"""
        pass

    def save(self, name, content, max_length=None):
        """保存文件时使用"""
        # name 文件名字
        # content 上传文件内容的File对象
        tracker_path = get_tracker_conf(self.client_conf)
        client = Fdfs_client(tracker_path)
        res = client.upload_appender_by_buffer(content.read())

        # @return dict {
        #     'Group name'      : group_name,
        #     'Remote file_id'  : remote_file_id,
        #     'Status'          : 'Upload successed.',
        #     'Local file name' : '',
        #     'Uploaded size'   : upload_size,
        #     'Storage IP'      : storage_ip
        # }
        if res.get('Status') != 'Upload successed.':
            raise Exception('上传文件到fast dfs失败')

        filename = res.get('Remote file_id')
        return filename.decode()

    def exists(self, name):
        """在save()函数之前执行,判断文件名是否可用，
        由于我没吧文件存到django服务器上，
        而是存到fdfs上，所以文件名都是可用的。"""
        return False

    def url(self, name):
        """返回访问文件的url路径"""
        return self.base_url + name
