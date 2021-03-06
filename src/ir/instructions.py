__author__ = 'sarangis'

from src.ir.utils import *
from src.ir.constants import *
from src.ir.validator import verify, Validator
from src.ir.exceptions import InvalidTypeException, NoBBTerminatorException

class InstructionList(list):
    def __init__(self, name_generator):
        list.__init__(self)
        self.__name_generator = name_generator

    def append(self, inst):
        if inst.needs_name:
            inst.name = self.__name_generator.generate(inst)

        list.append(self, inst)

    def insert(self, idx, inst):
        if inst.needs_name:
            inst.name = self.__name_generator.generate(inst)

        list.insert(self, idx, inst)


    def __add__(self, other):
        raise NotImplementedError("__add__ method not implemented for InstructionList")


class Instruction(Value):
    @verify(operands=list)
    def __init__(self, operands=[], parent=None, name=None, needs_name=True):
        Value.__init__(self)
        self.__parent = parent
        self.__inst_idx = -1
        self.__name = name
        self.__needs_name = needs_name

        self.operands = operands
        self.__uses = []

        for operand in operands:
            if isinstance(operand, Instruction):
                operand.add_use(self)

    def erase_from_parent(self):
        parent = self.__parent

        # Before removing any instruction from the parent make sure that all its uses
        # have no reference to this instruction.
        uses_remain = []
        for use in self.uses:
            if hasattr(use, "operands"):
                for op in use.operands:
                    if op == use:
                        uses_remain.append(use)

        if len(uses_remain) > 0:
            print("Instruction Deleted: %s" % str(self))
            for use in uses_remain:
                print("Use: %s" % str(use))
            raise Exception("Uses remain while current instruction is being deleted")

        for inst in parent.instructions:
            if inst == self:
                self.parent.instructions.remove(inst)

    @property
    def uses(self):
        return self.__uses

    def add_use(self, use):
        self.__uses.append(use)

    @property
    def needs_name(self):
        return self.__needs_name

    @property
    def parent(self):
        return self.__parent

    @parent.setter
    def parent(self, bb):
        self.__parent = bb

    @property
    def inst_idx(self):
        return self.__inst_idx

    @inst_idx.setter
    def inst_idx(self, v):
        self.__inst_idx = v

    @property
    def name(self):
        if self.__name is None:
            return None

        if self.__name[0] != "%":
            return "%" + self.__name
        else:
            return self.__name

    @name.setter
    def name(self, n):
        self.__name = n

    def __str__(self):
        pass

    __repr__ = __str__


class CallInstruction(Instruction):
    def __init__(self, func, arg_list, parent=None, name=None):
        Instruction.__init__(self, [func] + arg_list, parent, name)
        self.__func = func

        # Verify the Args
        self.__args = arg_list

    @property
    def function(self):
        return self.__func

    @property
    def args(self):
        return self.__args

    def __str__(self):
        output_str = "call " + " @" + self.__func.name

        output_str += render_list_with_parens(self.__args)

        return output_str

    __repr__ = __str__


class TerminateInstruction(Instruction):
    def __init__(self, parent=None, name=None):
        Instruction.__init__(self, [], parent, name)

    def __str__(self):
        pass


class ReturnInstruction(Instruction):
    def __init__(self, value=None, parent=None, name=None):
        Instruction.__init__(self, [value], parent, name, needs_name=False)

    @property
    def value(self):
        return self.operands[0]

    def __str__(self):
        if self.operands[0] is None:
            output_str = "return void"
        elif hasattr(self.operands[0], "name"):
            output_str = "return " + str(self.operands[0].name)
        else:
            output_str = "return " + str(self.operands[0])
        return output_str

    __repr__ = __str__


class SelectInstruction(Instruction):
    def __init__(self, cond, val_true, val_false, parent=None, name=None):
        Instruction.__init__(self, [cond, val_true, val_false], parent, name)
        self.__cond = cond
        self.__val_true = val_true
        self.__val_false = val_false

    @property
    def condition(self):
        return self.__cond

    @property
    def val_true(self):
        return self.__val_true

    @property
    def val_false(self):
        return self.__val_false

    def __str__(self):
        output_str = "select " + str(self.__cond) + " " + str(self.__val_true) + " " + str(self.__val_false)
        return output_str

    __repr__ = __str__


class LoadInstruction(Instruction):
    def __init__(self, alloca, parent=None, name=None):
        Instruction.__init__(self, [], parent, name, needs_name=True)

        assert isinstance(alloca, AllocaInstruction)
        self.__alloca = alloca

    def __str__(self):
        str = ""
        str += "load %s" % self.__alloca.name
        return str

class StoreInstruction(Instruction):
    def __init__(self, alloca, value, parent=None):
        Instruction.__init__(self, [], parent, name=None, needs_name=False)

        assert isinstance(alloca, AllocaInstruction)
        self.__alloca = alloca
        self.__value = value

    @property
    def alloca(self):
        return self.__alloca

    @property
    def value(self):
        return self.__value

    def __str__(self):
        str = ""
        str += "store %s, %s" % (self.__alloca.name, self.__value)
        return str


class BinOpInstruction(Instruction):
    OP_ADD = 0
    OP_SUB = 1
    OP_MUL = 2
    OP_DIV = 3

    def __init__(self, binop, lhs, rhs, parent=None, name=None):
        Instruction.__init__(self, [lhs, rhs], parent, name)
        self.__operator = binop

    @property
    def operator(self):
        return self.__operator

    @property
    def lhs(self):
        return self.operands[0]

    @property
    def rhs(self):
        return self.operands[1]

    def __str__(self):
        if self.__operator == BinOpInstruction.OP_ADD:
            output_str = "add"
        elif self.__operator == BinOpInstruction.OP_SUB:
            output_str = "sub"
        elif self.__operator == BinOpInstruction.OP_MUL:
            output_str = "mul"
        elif self.__operator == BinOpInstruction.OP_DIV:
            output_str = "div"
        else:
            raise InvalidTypeException("BinOp instruction expects, OP_ADD, OP_SUB, OP_MUL, OP_DIV")

        output_str += render_list_with_parens(self.operands)
        return output_str

    __repr__ = __str__


class AddInstruction(BinOpInstruction):
    def __init__(self, lhs, rhs, parent=None, name=None):
        BinOpInstruction.__init__(self, BinOpInstruction.OP_ADD, lhs, rhs, parent, name)


class SubInstruction(BinOpInstruction):
    def __init__(self, lhs, rhs, parent=None, name=None):
        BinOpInstruction.__init__(self, BinOpInstruction.OP_SUB, lhs, rhs, parent, name)


class MulInstruction(BinOpInstruction):
    def __init__(self, lhs, rhs, parent=None, name=None):
        BinOpInstruction.__init__(self, BinOpInstruction.OP_MUL, lhs, rhs, parent, name)


class DivInstruction(BinOpInstruction):
    def __init__(self, lhs, rhs, parent=None, name=None):
        BinOpInstruction.__init__(self, BinOpInstruction.OP_DIV, lhs, rhs, parent, name)


class AllocaInstruction(Instruction):
    def __init__(self, num_elms=None, parent=None, name=None):
        Instruction.__init__(self, [], parent, name, needs_name=True)
        self.__num_elms = num_elms

        if self.__num_elms is None:
            self.__num_elms = 1

    @property
    def num_elms(self):
        return self.__num_elms

    def __str__(self):
        output_str = "alloca [%s]*" % (self.__num_elms)
        return output_str

    __repr__ = __str__


class PhiInstruction(Instruction):
    def __init__(self, parent=None, name=None):
        Instruction.__init__(self, [], parent, name)

    def __str__(self):
        pass


class BranchInstruction(Instruction):
    def __init__(self, bb, parent=None, name=None):
        Instruction.__init__(self, [bb], parent, name, needs_name=False)
        self.__bb = bb

        if parent is not None:
            parent.add_successor(bb)
            bb.add_predecessor(parent)

    @property
    def basic_block(self):
        return self.__bb

    def __str__(self):
        output_str = "br " + self.__bb.name
        return output_str


class ConditionalBranchInstruction(Instruction):
    def __init__(self, cmp_inst, value, bb_true, bb_false, parent=None, name=None):
        Instruction.__init__(self, [cmp_inst, bb_true, bb_false], parent, name, needs_name=False)
        self.__cmp_inst = cmp_inst
        self.__value = value
        self.__bb_true = bb_true
        self.__bb_false = bb_false

        if parent is not None:
            parent.add_successor(bb_true)
            parent.add_successor(bb_false)
            bb_true.add_predecessor(parent)
            bb_false.add_predecessor(parent)

    @property
    def cmp_inst(self):
        return self.__cmp_inst

    @property
    def cmp_value(self):
        return self.__value

    @property
    def bb_true(self):
        return self.__bb_true

    @property
    def bb_false(self):
        return self.__bb_false

    def __str__(self):
        output_str = "br "
        output_str += self.__cmp_inst.name + " "
        output_str += str(self.__value) + ","
        output_str += " label %" + str(self.__bb_true.name) + ", label %" + str(self.__bb_false.name)
        return output_str


class IndirectBranchInstruction(BranchInstruction):
    def __init__(self, bb, parent=None, name=None):
        BranchInstruction.__init__(self, bb, parent, name)

    def __str__(self):
        pass


class SwitchInstruction(Instruction):
    def __init__(self, parent=None, name=None):
        Instruction.__init__(self, [], parent, name)

    def __str__(self):
        pass

class CompareTypes:
    EQ = 1
    NE = 2
    UGT = 3
    UGE = 4
    ULT = 5
    ULE = 6
    SGT = 7
    SGE = 8
    SLT = 9
    SLE = 10

    @staticmethod
    def get_str(compareTy):
        if compareTy == CompareTypes.EQ:
            return "eq"
        elif compareTy == CompareTypes.NE:
            return "ne"
        elif compareTy == CompareTypes.UGT:
            return "ugt"
        elif compareTy == CompareTypes.UGE:
            return "uge"
        elif compareTy == CompareTypes.ULT:
            return "ult"
        elif compareTy == CompareTypes.ULE:
            return "ule"
        elif compareTy == CompareTypes.SGT:
            return "sgt"
        elif compareTy == CompareTypes.SGE:
            return "sge"
        elif compareTy == CompareTypes.SLT:
            return "slt"
        elif compareTy == CompareTypes.SLE:
            return "sle"


class CompareInstruction(Instruction):
    def __init__(self, cond, op1, op2, parent=None, name=None):
        Instruction.__init__(self, [op1, op2], parent, name)
        self.__condition = cond
        self.__op1 = op1
        self.__op2 = op2

    @property
    def condition(self):
        return self.__condition

    @property
    def op1(self):
        return self.__op1

    @property
    def op2(self):
        return self.__op2

    def __str__(self):
        return "Compare Instruction"

    __repr__ = __str__


class ICmpInstruction(CompareInstruction):
    def __init__(self, cond, op1, op2, parent=None, name=None):
        CompareInstruction.__init__(self, cond, op1, op2, parent, name)

    def __str__(self):
        output_str = "icmp "
        output_str += CompareTypes.get_str(self.condition)
        output_str += " " + str(self.op1.name) + ", "

        if isinstance(self.op2, Number):
            output_str += str(self.op2)
        else:
            output_str += str(self.op2.name)
        return output_str

    __repr__ = __str__


class FCmpInstruction(CompareInstruction):
    def __init__(self, cond, op1, op2, parent=None, name=None):
        CompareInstruction.__init__(self, cond, op1, op2, parent, name)

    def __str__(self):
        output_str = "fcmp "
        output_str += CompareTypes.get_str(self.condition)
        output_str += " " + str(self.op1) + ", " + str(self.op2)
        return output_str


    __repr__ = __str__


class CastInstruction(Instruction):
    def __init__(self, parent=None, name=None):
        Instruction.__init__(self, [], parent, name)

    def __str__(self):
        pass

    __repr__ = __str__


class GEPInstruction(Instruction):
    def __init__(self, parent=None, name=None):
        Instruction.__init__(self, [], parent, name)

    def __str__(self):
        pass

    __repr__ = __str__


class ExtractElementInstruction(Instruction):
    def __init__(self, vec, idx, parent=None, name=None):
        Instruction.__init__(self, [], parent, name)
        self.__vec = vec
        self.__idx = idx

    @property
    def vec(self):
        return self.__vec

    @property
    def idx(self):
        return self.__idx

    def __str__(self):
        pass

    __repr__ = __str__


class InsertElementInstruction(Instruction):
    def __init__(self, parent=None, name=None):
        Instruction.__init__(self, [], parent, name)

    def __str__(self):
        pass

    __repr__ = __str__


class BitwiseBinaryInstruction(Instruction):
    SHL = 0
    LSHR = 1
    ASHR = 2
    AND = 3
    OR = 4
    XOR = 5

    def __init__(self, op, op1, op2, parent=None, name=None):
        Instruction.__init__(self, [op1, op2], parent, name)
        self.__op1 = op1
        self.__op2 = op2
        self.__operator = op

    @property
    def op1(self):
        return self.__op1

    @property
    def op2(self):
        return self.__op2

    def __str__(self):
        if self.__operator == BitwiseBinaryInstruction.SHL:
            output_str = "shl"
        elif self.__operator == BitwiseBinaryInstruction.LSHR:
            output_str = "lshr"
        elif self.__operator == BitwiseBinaryInstruction.ASHR:
            output_str = "ashr"
        elif self.__operator == BitwiseBinaryInstruction.AND:
            output_str = "and"
        elif self.__operator == BitwiseBinaryInstruction.OR:
            output_str = "or"
        elif self.__operator == BitwiseBinaryInstruction.XOR:
            output_str = "xor"
        else:
            raise InvalidTypeException("Invalid Bitwise Binary operator: %s encountered" % self.__operator)

        output_str += " " + str(self.__op1) + ", " + str(self.__op2)
        return output_str

    __repr__ = __str__


class ShiftLeftInstruction(BitwiseBinaryInstruction):
    def __init__(self, op1, op2, parent=None, name=None):
        BitwiseBinaryInstruction.__init__(self, BitwiseBinaryInstruction.SHL, op1, op2, parent, name)


class LogicalShiftRightInstruction(BitwiseBinaryInstruction):
    def __init__(self, op1, op2, parent=None, name=None):
        BitwiseBinaryInstruction.__init__(self, BitwiseBinaryInstruction.LSHR, op1, op2, parent, name)


class ArithmeticShiftRightInstruction(BitwiseBinaryInstruction):
    def __init__(self, op1, op2, parent=None, name=None):
        BitwiseBinaryInstruction.__init__(self, BitwiseBinaryInstruction.ASHR, op1, op2, parent, name)


class AndInstruction(BitwiseBinaryInstruction):
    def __init__(self, op1, op2, parent=None, name=None):
        BitwiseBinaryInstruction.__init__(self, BitwiseBinaryInstruction.AND, op1, op2, parent, name)


class OrInstruction(BitwiseBinaryInstruction):
    def __init__(self, op1, op2, parent=None, name=None):
        BitwiseBinaryInstruction.__init__(self, BitwiseBinaryInstruction.OR, op1, op2, parent, name)


class XorInstruction(BitwiseBinaryInstruction):
    def __init__(self, op1, op2, parent=None, name=None):
        BitwiseBinaryInstruction.__init__(self, BitwiseBinaryInstruction.XOR, op1, op2, parent, name)


class BasicBlock(Validator):
    def __init__(self, name, parent):
        name = parent.name_generator.generate_bb(name)
        self.__name = name
        self.__parent = parent
        self.__instructions = InstructionList(parent.name_generator)
        self.__predecessors = set()
        self.__successors = set()

    @property
    def predecessors(self):
        return self.__predecessors

    @property
    def successors(self):
        return self.__successors

    def add_predecessor(self, predecessor):
        self.__predecessors.add(predecessor)

    def add_successor(self, successor):
        self.__successors.add(successor)

    @property
    def name(self):
        return self.__name

    @property
    def instructions(self):
        return self.__instructions

    @property
    def parent(self):
        return self.__parent

    @parent.setter
    def parent(self, bb):
        self.__parent = bb

    def is_empty(self):
        if len(self.__instructions) == 0 or \
           isinstance(self.__instructions[-1], BranchInstruction):
            return True

        return False

    def get_terminator(self):
        inst = None
        if len(self.__instructions) > 0:
            inst = self.__instructions[-1]

        if isinstance(inst, ReturnInstruction) or isinstance(inst, BranchInstruction) or isinstance(inst, ConditionalBranchInstruction):
            return inst
        else:
            return None

    def has_terminator(self):
        if self.get_terminator() is not None:
            return True

        return False

    @verify(inst=Instruction)
    def find_instruction_idx(self, inst):
        for idx, i in enumerate(self.__instructions):
            if i == inst:
                return idx

        return None

    def validate(self):
        error_str = self.__name + " BB has not terminator instruction"
        # Get the last instruction and make sure its the terminator
        if len(self.__instructions) > 0:
            last_inst = self.__instructions[len(self.__instructions) - 1]
            if not is_terminator_instruction(last_inst):
                raise NoBBTerminatorException(error_str)
        else:
            raise NoBBTerminatorException(error_str)

    def render(self):
        predecessor_names = [p.name for p in self.__predecessors]

        output_str = ""
        if len(self.__predecessors) > 0:
            output_str += "\n"

        output_str += "<" + self.name + ">" + ": "
        if len(predecessor_names) > 0:
            output_str += "; pred: " + str(predecessor_names)

        output_str += "\n"
        for i in self.__instructions:
            output_str += " " * 4

            if i.name is not None:
                output_str += i.name + " = "

            output_str += str(i) + "\n"

        return output_str

    def __str__(self):
        return "<" + self.name + ">"

    __repr__ = __str__
