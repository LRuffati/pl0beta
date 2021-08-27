import src


def restore_regs(*regs,
                 section: str,
                 code: 'Code',
                 layout: 'StackLayout',
                 regalloc: 'AllocInfo'):
    code.comment("Restoring registers")
    pass


def save_registers(*regs,
                   section: str,
                   code: 'Code',
                   layout: 'StackLayout',
                   regalloc: 'AllocInfo'):
    code.comment("Saving registers")
    pass


if __name__ == '__main__':
    Code = src.Codegen.Code.Code
    StackLayout = src.Codegen.FrameUtils.StackLayout
    AllocInfo = src.Allocator.Regalloc.AllocInfo
