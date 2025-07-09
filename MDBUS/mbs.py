import serial 
import modbus_tk.defines as fnc
from modbus_tk import modbus_rtu as rtu
import time
import threading

class MBUS():
    def __init__(self, PORT='COM4', BOARD_RATE=38400, TOUT=1):
        """
        Modbus RTU 通信类初始化
        """
        self.PORT = PORT
        self.BOARD_RATE = BOARD_RATE
        self.TOUT = TOUT
        # 通信参数


        self.isopend = False
        self.master = None
        self.end = False
        # 传递信号量

        self.func = 0  
        self.config = []
        self.distance = []
        self.values = [0,0,0,0,0]
        #电机运动参数

        self.ADR_IN = 0
        self.NUM_IN = 6
        self.ADR_COIL = 0
        self.NUM_COIL = 5
        # 受控设备


        self.registers = [0]*6
        self.coils = [0]*5
        # input寄存器状态和线圈状态
        

        self.sender = threading.Thread(target=self.beating)
        # 发指令线程
        self.beating_interval = 0.1  
        # 默认心跳间隔

    def open(self):
        """打开Modbus RTU串口连接"""
        print(f"打开端口: {self.isopend}, {self.PORT}, {self.BOARD_RATE}, {self.TOUT}")
        if self.isopend:
            raise Exception(f'端口已经打开: {self.PORT}')
        # 创建Modbus RTU主站
        self.master = rtu.RtuMaster(
            serial.Serial(
                port=self.PORT,
                baudrate=self.BOARD_RATE,
                parity='N',
                stopbits=1,
                timeout=0.5
            )
        )
        self.master.set_timeout(self.TOUT)
        self.master.set_verbose(False)  # 启/停用详细日志
        self.master.open()
        self.isopend = True


    def set_speed(self):    
        """
        此函数修改电机控制板正反转速度
        """
        for s in self.config:
            int_value = int(s[1]) #原精度为三位小数，受控端会将整数转化为小数
            # 2. 拆分高低16位
            high_word1 = (int_value >> 16) & 0xFFFF  # 高16位（右移16位）
            low_word1 = int_value & 0xFFFF

            int_value = int(s[2])  
            high_word2 = (int_value >> 16) & 0xFFFF  # 高16位（右移16位）
            low_word2 = int_value & 0xFFFF
            print(s[0],s[1],s[2],"\n")
            print(f"id\t{s[0]-1},\nhigh_word1\t{high_word1},\nlow_word1\t{low_word1},\nhigh_word2\t{high_word2},\nlow_word2\t{low_word2}")
            try:
                self.master.execute(
                    slave= s[0],
                    function_code=fnc.WRITE_MULTIPLE_REGISTERS,
                    starting_address = 404,
                    quantity_of_x = 2,
                    output_value=[low_word1,high_word1]
                )
                time.sleep(0.1)
                self.master.execute(
                    slave= s[0],
                    function_code=fnc.WRITE_MULTIPLE_REGISTERS,
                    starting_address = 408,
                    quantity_of_x = 2,
                    output_value=[low_word2,high_word2]
                )
                time.sleep(0.1)
            except Exception as e:
                print(f"设置速度错误: sid{s[0]}{e}")
            
    def set_distance(self):    
        """
        此函数修改电机控制板正反转速度
        """
        for s in self.config:

            int_value = int(s[3]*1000)  # 100.000 → 100000
            # 2. 拆分高低16位
            high_word1 = (int_value >> 16) & 0xFFFF  # 高16位（右移16位）
            low_word1 = int_value & 0xFFFF
            print(f"id\t{s[0]-1},\nhigh_word1\t{high_word1},\nlow_word1\t{low_word1}")
            try:
                self.master.execute(
                    slave= s[0],
                    function_code=fnc.WRITE_MULTIPLE_REGISTERS,
                    starting_address = 402,
                    quantity_of_x = 2,
                    output_value=[low_word1,high_word1]
                )
            except Exception as e:
                print(f"设置距离错误: sid{s[0]}{e}")
    def close(self):
        """关闭Modbus RTU串口连接"""
        if not self.isopend:
            raise Exception(f'端口未打开: {self.PORT}')
        self.master.close()
        self.isopend = False

    def in_once(self):
        """
        读取输入寄存器
        
        参数:
            ADR: 起始地址 (默认:0)
            NUM: 读取数量 (默认:8)
        
        返回:
            读取的值存储在self.registers中
        """
        try:
            self.registers = self.master.execute(
                1,
                fnc.READ_INPUT_REGISTERS,
                self.ADR_IN,
                self.NUM_IN
            )
        except Exception as e:
                print(f"输入寄存器错误: {e}")
    def beating(self):
        """
        心跳发送指令：默认读取输入，如果传参则写/设置
        使用self.in_beating_interval作为间隔时间
        """
        while True:
            if self.end:
                break
            if not self.isopend:
                time.sleep(0.5)
                continue
            time.sleep(self.beating_interval)
            func = self.func
            if func == 0:
                self.in_once()
                print("test in")
            elif func == 1:
                self.coil_once()
                self.func = 0

            elif func == 2:
                self.set_speed()
                self.set_distance()
                self.func = 0


    
    def set_coil(self,ADR,NUM,values,func):
            self.ADR_COIL = ADR
            self.NUM_COIL = NUM
            self.values = values
            self.func = func

    def coil_once(self):
        """
        控制多个线圈
        
        参数:
            ADR: 起始地址 (默认:0)
            NUM: 线圈数量 (默认:8)
            values: 控制值列表 (默认:全部断开)
                   [62580]表示闭合, [0]表示断开
        """
        if self.values is None:
            VALUES = [0] * self.NUM_COIL         
        else :
            VALUES = self.values
        try:
            self.master.execute(
                1,
                fnc.WRITE_MULTIPLE_COILS,
                starting_address=self.ADR_COIL,
                quantity_of_x=self.NUM_COIL,
                output_value=VALUES
            )
        except Exception as e:
                print(f"控制失败: {e}")
                self.func = 1
                #控制失败不代表电机不转，但是为了保险再次发出控制指令
        
    def read_coils(self):
        try:    
            self.coils = list(self.master.execute(
                1,
                fnc.READ_COILS,
                0,
                5)
            )
        except Exception as e:
                print(f"读取失败: {e}")
    def set_salarate(self,id,value):
        int_value = int(value) 
        # 2. 拆分高低16位
        high_word1 = (int_value >> 16) & 0xFFFF  # 高16位（右移16位）
        low_word1 = int_value & 0xFFFF
        print(f"id\t{id-1},\nhigh_word1\t{high_word1},\nlow_word1\t{low_word1}")
        try:
            self.master.execute(
                slave= id,
                function_code=fnc.WRITE_MULTIPLE_REGISTERS,
                starting_address = 436,
                quantity_of_x = 2,
                output_value=[low_word1,high_word1]
            )
            self.master.execute(
                slave= id,
                function_code=fnc.WRITE_MULTIPLE_REGISTERS,
                starting_address = 438,
                quantity_of_x = 2,
                output_value=[low_word1,high_word1]
            )
        except Exception as e:
            print(f"设置距离错误: sid{id}{e}")

def main(): 
    """主函数示例"""
    PORT = 'COM4'
    BOARD_RATE = 38400
    
    ser = MBUS( PORT, BOARD_RATE, 5)
    ser.open()
    # ser.config.append([2,1781,1781,100])
    # ser.config.append([3,1781,1781,100])
    # ser.config.append([4,1781,1781,100])
    # ser.config.append([5,1781,1781,100])
    # ser.config.append([6,1781,1781,100])

    # ser.set_speed()
    # ser.set_distance()
    ser.set_salarate(2,4000)
    ser.set_salarate(3,2000)

    time.sleep(1)

    ser.close()
    print("end")




if __name__ == "__main__":
    main()