import cmd
import logging
import os
from pathlib import Path
from typing import Dict
import re
import shutil

## 设置区域
# 需要接管的存档文件夹
SAVE_DIR = './www/save'
# Save Manager工作时存储文件的文件夹
# SM_WORKING_DIR = SAVE_DIR
SM_WORKING_DIR = './www/save_manager'
# 原游戏的存档文件名格式，可用slot变量
GAME_SAVE_FMT = r'file{slot}.rpgsave'
# Save Manager的存档名字，可用id和memo变量
SM_SAVE_FMT = r'{id}_{memo}.save.sm'
# Save Manager的映射名字，可用id和slot变量
SM_MAPPING_FMT = r'slot_{slot}-id_{id}.mapping.sm'

## ---------实现开始-------
DESCRIPTION = f'''
Save Manager v2.0 by Maxlinn, 2022
本工具适用于 游戏存档位置不够 或者 想要给存档写记录保存 的场景
# 术语
slot:
    原游戏的存档系统每个槽位称为slot
id:
    Save Manager 会有一套独立的存档编号，称为id，从0开始
memo:
    Save Manager 允许给其管理的存档增加备忘，称为memo。将会使用文件名来存储，所以请注意格式。
# 文件
{SM_SAVE_FMT}:
    Save Manager 存储的存档
{SM_MAPPING_FMT}：
    Save Manager 需要额外记住游戏的各个slot正在使用哪些id的存档
# 第一次使用，请使用 help 命令查看命令列表，使用 help <子命令> 查看使用方法
'''
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SaveManager(object):

    def __init__(self,
                 game_save_dir: Path,
                 working_dir: Path,
                 game_save_fmt: str,
                 sm_save_fmt: str,
                 sm_mapping_fmt: str):
        ## 路径管理
        assert game_save_dir.exists() and game_save_dir.is_dir()
        self.game_save_dir = game_save_dir
        os.makedirs(working_dir, exist_ok=True)
        self.working_dir = working_dir
        ## 文件名格式管理
        assert 'slot' in game_save_fmt
        self.game_save_fmt = game_save_fmt
        self.game_save_regex = re.sub(r'{.*?}', '(.*?)', self.game_save_fmt)

        assert 'id' in sm_save_fmt and 'memo' in sm_save_fmt
        assert sm_save_fmt.index('id') < sm_save_fmt.index('memo')
        self.sm_save_fmt = sm_save_fmt
        self.sm_save_regex = re.sub(r'{.*?}', '(.*?)', self.sm_save_fmt)

        assert 'slot' in sm_mapping_fmt and 'id' in sm_mapping_fmt
        assert sm_mapping_fmt.index('slot') < sm_mapping_fmt.index('id')
        self.sm_mapping_fmt = sm_mapping_fmt
        self.sm_mapping_regex = re.sub(r'{.*?}', '(.*?)', self.sm_mapping_fmt)

        ## 数据结构
        self.saves: Dict[int, Path] = {}  # id_ -> Path(sm_save_file)
        self.slot2id: Dict[str, int] = {}  # slot -> id_ ，因为有的游戏slot不是递增的正整数

        self.reload_sm()

    @staticmethod
    def _copyfile(src_p: Path, target: Path):
        assert isinstance(src_p, Path) and isinstance(target, Path)
        shutil.copy(str(src_p), str(target))

    def reload_sm(self):
        if not (self.game_save_dir.exists() and self.game_save_dir.is_dir()):
            raise Exception('存档路径不存在或者不是文件夹')
        # 清空
        self.saves.clear()
        self.slot2id.clear()
        # 检查所有文件
        for p in self.working_dir.glob('*'):
            # 匹配存档
            t = re.findall(self.sm_save_regex, p.name)
            if t:
                id_str, _ = t[0]
                self.saves[int(id_str)] = p
                continue
            # 匹配映射
            t = re.findall(self.sm_mapping_regex, p.name)
            if t:
                slot, id_str = t[0]
                self.slot2id[slot] = int(id_str)
                continue

    def save(self, slot: str, memo: str, id_: int = None) -> int:
        # id_为-1时，将会自增，否则使用指定的
        # 返回存到的存档id
        if id_ is None:
            id_ = max(self.saves.keys()) + 1 if self.saves else 0

        slot_p = self.game_save_dir / self.game_save_fmt.format(slot=slot)
        if not slot_p.exists():
            raise Exception(f'游戏存档文件不存在 {slot_p}')

        sm_save_p = self.working_dir / self.sm_save_fmt.format(id=id_, memo=memo)
        try:
            self._copyfile(slot_p, sm_save_p)
        except Exception as e:
            raise Exception(f'存档失败，请检查memo内是否有非文件名允许的字符，报错为 {repr(e)}')
        else:
            self.saves[id_] = sm_save_p
            self.slot2id[slot] = id_
            sm_mapping_p = self.working_dir / self.sm_mapping_fmt.format(slot=slot, id=id_)
            sm_mapping_p.touch(exist_ok=True)
            return id_

    def load(self, id_: int, slot: str):
        sm_save_p = self.saves.get(id_)
        if sm_save_p is None:
            raise Exception('存档管理器不存在 {id_} 号')

        slot_p = self.game_save_dir / self.game_save_fmt.format(slot=slot)
        id_old = self.slot2id.get(slot)
        if id_old is None:
            # 游戏 {slot} 槽位还没有数据，将填入 {id_} 号存档
            self._copyfile(sm_save_p, slot_p)
            # 更新映射
            self.slot2id[slot] = id_
            sm_mapping_p = self.working_dir / self.sm_mapping_fmt.format(slot=slot, id=id_)
            sm_mapping_p.touch(exist_ok=True)
        else:
            # 游戏 {slot} 槽位有数据，将用 {id_} 号存档覆盖
            self._copyfile(sm_save_p, slot_p)
            # 更新映射
            self.slot2id[slot] = id_
            sm_mapping_p = self.working_dir / self.sm_mapping_fmt.format(slot=slot, id=id_)
            sm_mapping_p_old = self.working_dir / self.sm_mapping_fmt.format(slot=slot, id=id_old)
            sm_mapping_p_old.rename(sm_mapping_p)

    def memo(self, id_: int, memo: str):
        sm_save_p_old = self.saves[id_]
        sm_save_p = self.working_dir / self.sm_save_fmt.format(id=id_, memo=memo)
        sm_save_p_old.rename(sm_save_p)
        self.saves[id_] = sm_save_p

    def tabular(self, width: int = 10) -> str:
        res = ''
        res += '\t'.join(['id'.center(width), 'slot'.center(width), 'memo'.center(width)])
        res += '\n'

        id2slot = dict(zip(self.slot2id.values(), self.slot2id.keys()))
        for id_, p in self.saves.items():
            res += (f'{str(id_).center(width)}\t'
                    f'{str(id2slot.get(id_, "")).center(width)}\t'
                    f'{p.name.center(width)}')
            res += '\n'
        return res

    def init_from_game(self) -> int:
        # 从游戏存档文件夹里批量导入
        # 返回导入的存档个数
        cnt = 0
        for p in self.game_save_dir.glob('*'):
            t = re.findall(self.game_save_regex, p.name)
            if not t:
                continue
            slot = t[0]
            self.save(slot=slot, memo='批量导入')
            cnt += 1
        return cnt


class ManagerCmd(cmd.Cmd, SaveManager):
    def __init__(self, **kwargs):
        cmd.Cmd.__init__(self)
        SaveManager.__init__(self, **kwargs)

        self.prompt = '(Save Manager)>>> '
        self.intro = DESCRIPTION
        self.reload_sm()
        logger.info(f'读取到了 {len(self.saves)} 个存档管理器存档，{len(self.slot2id)} 个映射')

    def do_list(self, arg):
        '''展示所有的存档文件状态'''
        res = self.tabular()
        print(res)
        logger.info('\n')
        logger.info(f'已展示 {len(self.saves)} 个存档')

    def do_save(self, args: str):
        '''save [slot] [memo='']，将游戏的slot编号槽位存储到新的id，并且增加记录为memo'''
        t = args.split(' ')

        if len(t) == 1:
            slot, memo = t[0]
        elif len(t) == 2:
            slot, memo = t[0], t[1]
        else:
            logger.error(f'不合法的参数组合 {args}')
            return

        try:
            id_ = self.save(slot=slot, memo=memo)
        except Exception as e:
            logger.error(repr(e))
            return
        else:
            logger.info(f'已存储slot[{slot}]到id[{id_}]位置，备注为{memo}')

    def do_load(self, args):
        '''load [id] [slot]，将id号存档加载到游戏的slot槽位'''
        t = args.split(' ')
        id_, slot = int(t[0]), t[1]

        try:
            self.load(id_=id_, slot=slot)
        except Exception as e:
            logger.error(repr(e))
        else:
            logger.info(f'已加载id[{id_}]:"{self.saves[id_]}"到slot[{slot}]')

    def do_reload_sm(self, args):
        '''重新从工作文件夹加载存档状态，比如自己手动修改了工作文件夹下的内容'''
        self.reload_sm()
        logger.info('已重新载入')

    def do_memo(self, args):
        '''memo [id] [memo=""] 重新设置id号存档的便签memo'''
        t = args.split(' ')

        if len(t) == 1:
            id_, memo = int(t[0]), ''
        elif len(t) == 2:
            id_, memo = int(t[0]), t[1]
        else:
            logger.error(f'不合法的参数组合 {args}')
            return

        try:
            sm_save_p_old = self.saves[id_]
            self.memo(id_=id_, memo=memo)
            sm_save_p_new = self.saves[id_]
        except Exception as e:
            logger.error(repr(e))
        else:
            logger.info(f'已将[{id_}]号文件名修改为{sm_save_p_new.name}，之前为{sm_save_p_old.name}')

    def do_init_from_game(self, args):
        '''批量添加游戏已有的存档到存档管理器，适用于玩了一段时间后第一次使用存档管理器'''
        cnt = self.init_from_game()
        logger.info(f'已完成批量导入{cnt}条，目前共有{len(self.saves)}条存档')


if __name__ == '__main__':
    cmd = ManagerCmd(
        game_save_dir=Path(SAVE_DIR),
        working_dir=Path(SM_WORKING_DIR),
        game_save_fmt=GAME_SAVE_FMT,
        sm_save_fmt=SM_SAVE_FMT,
        sm_mapping_fmt=SM_MAPPING_FMT
    )
    cmd.cmdloop()
