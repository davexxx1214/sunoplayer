import json
import re
import plugins
from bridge.reply import Reply, ReplyType
from bridge.context import ContextType
from channel.chat_message import ChatMessage
from plugins import *
from common.log import logger
from common.tmp_dir import TmpDir

import os
import uuid
from suno import SongsGen
import os
import uuid
from glob import glob

@plugins.register(
    name="sunoplayer",
    desire_priority=2,
    desc="A plugin to call suno API",
    version="0.0.1",
    author="davexxx",
)

class sunoplayer(Plugin):
    def __init__(self):
        super().__init__()
        try:
            curdir = os.path.dirname(__file__)
            config_path = os.path.join(curdir, "config.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            else:
                # 使用父类的方法来加载配置
                self.config = super().load_config()

                if not self.config:
                    raise Exception("config.json not found")
            
            # 设置事件处理函数
            self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
            # 从配置中提取所需的设置
            self.cookie = self.config.get("cookie","")
            self.show_lyc = self.config.get("show_lyc",False)
            self.suno_prefix = self.config.get("suno_prefix", "suno")
            self.custom_suno_prefix = self.config.get("custom_suno_prefix", "custom")

            # 初始化成功日志
            logger.info("[sunoplayer] inited.")
        except Exception as e:
            # 初始化失败日志
            logger.warn(f"sunoplayer init failed: {e}")
    def on_handle_context(self, e_context: EventContext):
        context = e_context["context"]
        if context.type not in [ContextType.TEXT, ContextType.SHARING,ContextType.FILE,ContextType.IMAGE]:
            return
        content = context.content

        if e_context['context'].type == ContextType.TEXT:
            if content.startswith(self.suno_prefix):
                # Call new function to handle search operation
                pattern = self.suno_prefix + r"\s(.+)"
                match = re.match(pattern, content)
                if match: ##   匹配上了suno的指令
                    logger.info("calling suno service")
                    prompt = content[len(self.suno_prefix):].strip()
                    logger.info(f"suno prompt = : {prompt}")
                    try:
                        custom = False
                        self.call_suno_service(prompt,custom, e_context)
                    except Exception as e:
                        logger.error("create song error: {}".format(e))
                        rt = ReplyType.TEXT
                        rc = "服务暂不可用,可能是某些词汇没有通过安全审查"
                        reply = Reply(rt, rc)
                        e_context["reply"] = reply
                        e_context.action = EventAction.BREAK_PASS
                else:
                    tip = f"💡欢迎使用写歌服务，指令格式为:\n\n{self.suno_prefix}+ 空格 + 对歌曲主题的描述(控制在30个字之内)\n例如:\n{self.suno_prefix} 一首浪漫的情歌\n或者:\n{self.suno_prefix} a blue cyber dream song"
                    reply = Reply(type=ReplyType.TEXT, content= tip)
                    e_context["reply"] = reply
                    e_context.action = EventAction.BREAK_PASS

            if content.startswith(self.custom_suno_prefix):
                # Call new function to handle search operation
                pattern = self.custom_suno_prefix + r"\s(.+)"
                match = re.match(pattern, content)
                if match: ##   匹配上了custom的指令
                    logger.info("calling custom suno service")
                    prompt = content[len(self.custom_suno_prefix):].strip()
                    logger.info(f"custom suno prompt =  {prompt}")
                    try:
                        custom = True
                        self.call_suno_service(prompt, custom, e_context)
                    except Exception as e:
                        logger.error("create song error: {}".format(e))
                        rt = ReplyType.TEXT
                        rc = "服务暂不可用,可能是某些词汇没有通过安全审查"
                        reply = Reply(rt, rc)
                        e_context["reply"] = reply
                        e_context.action = EventAction.BREAK_PASS
                else:
                    tip = f"💡欢迎使用填词作曲服务，指令格式为:\n\n{self.custom_suno_prefix}+ 空格 + 完整歌词\n例如:\n{self.custom_suno_prefix} 在沉默的夜，星辰轻语，梦开始起航，穿越寂寞沙漠\n或者:\n{self.custom_suno_prefix} Whispers of night, where stars gently sigh, Dreams set to sail, cross the lonely sky"
                    reply = Reply(type=ReplyType.TEXT, content= tip)
                    e_context["reply"] = reply
                    e_context.action = EventAction.BREAK_PASS
                

    def call_suno_service(self, prompt, custom, e_context):
        cookie_str =f'{self.cookie}'

        output_dir = self.generate_unique_output_directory(TmpDir().path())
        logger.info(f"output dir = {output_dir}")
        song_detail = prompt

        i = SongsGen(cookie_str)  # Now 'cookie_str' is properly formatted as a Python string
        logger.info(f"credit left =  {i.get_limit_left()} ")
        if i.get_limit_left() < 1:
            logger.info("No enough credit left.")
            rt = ReplyType.TEXT
            rc = "账户额度不够，请联系管理员"
            reply = Reply(rt, rc)
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS
            return

        tip = '您的作曲之旅已经启航，让我们的音乐小精灵带上您的歌词飞向创意的宇宙！请耐心等待2~5分钟，您的个人音乐风暴就会随着节拍轻轻降落。准备好一起摇摆吧！🚀'
        self.send_reply(tip, e_context)

        if custom:
            logger.info("custom mode")
            i.save_songs(song_detail, output_dir, is_custom=True, title='歌词') 
        else:
            logger.info("theme mode")
            i.save_songs(song_detail, output_dir)


        # 查找 output_dir 中的 mp3 文件，这里假设每次调用只产生一个 mp3
        mp3_files = glob(os.path.join(output_dir, '*.mp3'))
        if mp3_files:
            mp3_file_path = mp3_files[0]
            if self.is_valid_file(mp3_file_path):
                logger.info("The MP3 file is valid.")
                newfilepath = self.rename_file(mp3_file_path, prompt)
                rt = ReplyType.FILE
                rc = newfilepath

            else:
                rt = ReplyType.TEXT
                rc = "生成失败"
                logger.info("The MP3 file is invalid or incomplete.")

            reply = Reply(rt, rc)
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS
        else:
            logger.info("No MP3 files found in the output directory.")
            rt = ReplyType.TEXT
            rc = "生成失败，服务不可用"
            reply = Reply(rt, rc)
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS

        # 查找 output_dir 中的 lrc 文件，这里我们不需要文件名
        lrc_file_path  = self.find_lrc_files(output_dir)
        if lrc_file_path :
            logger.info("LRC file found. path = {lrc_file_path }")
            if(self.show_lyc):
                msg = self.print_file_contents(lrc_file_path)
                self.send_reply(msg, e_context)

        else:
            logger.info("No LRC files found in the output directory.")

    def is_valid_file(self, file_path, min_size=100*1024):  # 100KB
        """Check if the file exists and is greater than a given minimum size in bytes."""
        return os.path.exists(file_path) and os.path.getsize(file_path) > min_size

    def find_lrc_files(self, directory):
        """Find the first .lrc file in a directory."""
        lrc_files = glob(os.path.join(directory, '*.lrc'))
        return lrc_files[0] if lrc_files else None

    def generate_unique_output_directory(self, base_dir):
        """Generate a unique output directory using a UUID."""
        unique_dir = os.path.join(base_dir, str(uuid.uuid4()))
        os.makedirs(unique_dir, exist_ok=True)
        return unique_dir

    def print_file_contents(self, file_path):
        """Read and print the contents of the file."""
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
        
    def send_reply(self, reply, e_context: EventContext, reply_type=ReplyType.TEXT):
        if isinstance(reply, Reply):
            if not reply.type and reply_type:
                reply.type = reply_type
        else:
            reply = Reply(reply_type, reply)
        channel = e_context['channel']
        context = e_context['context']
        # reply的包装步骤
        rd = channel._decorate_reply(context, reply)
        # reply的发送步骤
        return channel._send_reply(context, rd)
    
    def rename_file(self, filepath, prompt):
        # 提取目录路径和扩展名
        dir_path, filename = os.path.split(filepath)
        file_ext = os.path.splitext(filename)[1]

        # 移除prompt中的标点符号和空格
        cleaned_content = re.sub(r'[^\w]', '', prompt)
        # 截取prompt的前10个字符
        content_prefix = cleaned_content[:10]
                
        # 组装新的文件名
        new_filename = f"{content_prefix}"

        # 拼接回完整的新文件路径
        new_filepath = os.path.join(dir_path, new_filename + file_ext)

        # 重命名原文件
        try:
            os.rename(filepath, new_filepath)
        except OSError as e:
            logger.error(f"Error: {e.strerror}")
            return filepath

        return new_filepath