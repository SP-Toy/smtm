"""시뮬레이터

SimulationOperator를 사용해서 시뮬레이션을 컨트롤하는 모듈
"""
import signal
import time
from . import (
    LogManager,
    Analyzer,
    SimulationTrader,
    SimulationDataProvider,
    StrategyBuyAndHold,
    StrategySma0,
    SimulationOperator,
    DateConverter,
)


class Simulator:
    """smtm 시뮬레이터"""

    MAIN_STATEMENT = "input command (h:help): "

    def __init__(self, end=None, count=100, interval=2, strategy=0, from_dash_to=None):
        self.logger = LogManager.get_logger("Simulator")
        self.__terminating = False
        self.end = "2020-12-20T16:23:00Z"
        self.count = 100
        self.interval = interval
        self.operator = None
        self.strategy = int(strategy)
        self.budget = 50000
        self.is_initialized = False
        self.command_list = []
        self.create_command()

        if self.strategy != 0 and self.strategy != 1:
            self.strategy = 0
            print(f"invalid strategy: {self.strategy}, replaced with 0")

        if end is not None:
            self.end = end.replace("T", " ")

        if count is not None:
            self.count = count

        if from_dash_to is not None:
            dt = DateConverter.to_end_min(from_dash_to)
            self.end = dt[0]
            self.count = dt[1]

        if interval is not None:
            self.interval = float(self.interval)

    def create_command(self):
        """명령어 생성"""
        self.command_list = [
            {
                "guide": "h, help          print command info",
                "cmd": "help",
                "short": "h",
                "need_value": False,
                "action": self.print_help,
            },
            {
                "guide": "r, run           start running simulation",
                "cmd": "run",
                "short": "r",
                "need_value": False,
                "action": self.start,
            },
            {
                "guide": "s, stop          stop running simulation",
                "cmd": "stop",
                "short": "s",
                "need_value": False,
                "action": self._stop,
            },
            {
                "guide": "t, terminate     terminate simulator",
                "cmd": "terminate",
                "short": "t",
                "need_value": False,
                "action": self.terminate,
            },
            {
                "guide": "q, query         query and print current state or return score",
                "cmd": "query",
                "short": "q",
                "need_value": True,
                "value_guide": "input query target (ex. state, score, result) :",
                "action_with_value": self._on_query_command,
            },
            {
                "guide": "e, end           set simulation period end datetime",
                "cmd": "end",
                "short": "e",
                "need_value": True,
                "value_guide": "input simulation period end datetime(ex. 2020-12-20T18:00:00Z) :",
                "action_with_value": self._set_end,
            },
            {
                "guide": "c, count         set simulation count",
                "cmd": "count",
                "short": "c",
                "need_value": True,
                "value_guide": "input simulation count (ex. 100) :",
                "action_with_value": self._set_count,
            },
            {
                "guide": "int, interval    set simulation interval",
                "cmd": "interval",
                "short": "int",
                "need_value": True,
                "value_guide": "input simulation interval in seconds (ex. 0.5) :",
                "action_with_value": self._set_interval,
            },
            {
                "guide": "b, budget        set simulation budget",
                "cmd": "budget",
                "short": "b",
                "need_value": True,
                "value_guide": "input starting budget (ex. 70000) :",
                "action_with_value": self._set_budget,
            },
            {
                "guide": "st, strategy     set strategy",
                "cmd": "strategy",
                "short": "st",
                "need_value": True,
                "value_guide": "input strategy number 0: buy and hold, 1: SMA-0 :",
                "action_with_value": self._set_strategy,
            },
            {
                "guide": "l, log           set stream log level",
                "cmd": "log",
                "short": "l",
                "need_value": True,
                "value_guide": "set level (CRITICAL=50, ERROR=40, WARN=30, INFO=20, DEBUG=10) :",
                "action_with_value": self._set_log_level,
            },
            {
                "guide": "i, initialize    initialize simulation",
                "cmd": "initialize",
                "short": "i",
                "need_value": False,
                "action": self.initialize,
            },
        ]

    def main(self):
        """main 함수"""

        self.logger.info(f"end: {self.end}")
        self.logger.info(f"count: {self.count}")
        self.logger.info(f"interval: {self.interval}")
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

        while not self.__terminating:
            try:
                key = input(self.MAIN_STATEMENT)
                self.on_command(key)
            except EOFError:
                break

    def run_single(self):
        """단독으로 1회 실행"""
        self.initialize()
        self.start()
        while self.operator.state == "running":
            time.sleep(0.5)

        self.terminate()

    def print_help(self):
        """가이드 문구 출력"""
        print("command list =================")
        for item in self.command_list:
            print(item["guide"])

    def on_command(self, key):
        """커맨드 처리"""
        value = None
        for cmd in self.command_list:
            if cmd["cmd"] == key.lower() or cmd["short"] == key.lower():
                if cmd["need_value"]:
                    value = input(cmd["value_guide"])
                self.execute_command(key, value)
                return
        print("invalid command")

    def execute_command(self, command, value):
        """가이드 문구 출력"""
        for cmd in self.command_list:
            if cmd["cmd"] == command.lower() or cmd["short"] == command.lower():
                if cmd["need_value"]:
                    cmd["action_with_value"](value)
                else:
                    cmd["action"]()
                return
        print("invalid command")

    def _on_query_command(self, value):
        """가이드 문구 출력"""
        key = value.lower()
        if key in ["state", "1"]:
            print(self.operator.state)
        elif key in ["score", "2"]:
            self._get_score()
        elif key in ["result", "3"]:
            print(self.operator.get_trading_results())

    def _set_end(self, value):
        self.end = value.replace("T", " ")

    def _set_count(self, value):
        next_value = int(value)
        if next_value > 0:
            self.count = next_value

    def _set_interval(self, value):
        next_value = float(value)
        if next_value > 0:
            self.interval = next_value

    def _set_budget(self, value):
        next_value = int(value)
        if next_value > 0:
            self.budget = next_value

    def _set_strategy(self, value):
        if value == "0":
            self.strategy = 0
        elif value == "1":
            self.strategy = 1

    @staticmethod
    def _set_log_level(value):
        LogManager.set_stream_level(int(value))

    def _get_score(self):
        def print_score_and_main_statement(score):
            print("current score ==========")
            print(score)
            print(self.MAIN_STATEMENT)

        self.operator.get_score(print_score_and_main_statement)

    def initialize(self):
        """시뮬레이션 초기화"""
        if self.strategy == 0:
            strategy = StrategyBuyAndHold()
        else:
            strategy = StrategySma0()
        strategy.is_simulation = True
        self.operator = SimulationOperator()

        print("##### simulation is intialized #####")
        print(f"end: {self.end}")
        print(f"count: {self.count}")
        print(f"interval: {self.interval}")
        print("====================================")

        end_str = self.end.replace(" ", "T")
        data_provider = SimulationDataProvider()
        data_provider.initialize_simulation(end=end_str, count=self.count)
        trader = SimulationTrader()
        trader.initialize_simulation(end=end_str, count=self.count, budget=self.budget)
        analyzer = Analyzer()
        analyzer.is_simulation = True
        self.operator.initialize(
            data_provider,
            strategy,
            trader,
            analyzer,
            budget=self.budget,
        )
        self.operator.set_interval(self.interval)
        self.is_initialized = True

    def start(self):
        """시뮬레이션 시작, 재시작"""
        if self.is_initialized is not True:
            print("Not initialized")
            return

        self.logger.info("Simulation start! ==================")
        self.logger.info(f"end: {self.end}, count: {self.count}")

        if self.operator.start() is not True:
            print("Fail operator start")
            return

    def stop(self, signum, frame):
        """시뮬레이션 중지"""
        self._stop()
        self.__terminating = True
        print(f"Receive Signal {signum} {frame}")
        print("Stop Singing")

    def _stop(self):
        if self.operator is not None:
            self.operator.stop()

    def terminate(self):
        """시뮬레이터 종료"""
        print("Terminating......")
        self._stop()
        self.__terminating = True
        print("Good Bye~")
