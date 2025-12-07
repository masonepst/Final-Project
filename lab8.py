import time
import multiprocessing
from shifter import Shifter


class Stepper:
    num_steppers = 0
    shifter_outputs = multiprocessing.Value('i', 0)
    seq = [0b0001,0b0011,0b0010,0b0110,0b0100,0b1100,0b1000,0b1001]
    delay = 1200
    steps_per_degree = 1024/360

    def __init__(self, shifter, lock, newlock):
        self.s = shifter
        self.angle = multiprocessing.Value('d', 0.0)     # shared angle
        self.step_state = multiprocessing.Value('i', 0)  # shared step index
        self.busy = multiprocessing.Value('b', 0)        # 1 if rotating

        self.shifter_bit_start = 4 * Stepper.num_steppers
        self.lock = lock
        self.newlock = newlock

        Stepper.num_steppers += 1

    def __sgn(self, x):
        if x == 0:
            return 0
        return 1 if x > 0 else -1

    def __step(self, dir, angle, step_state):
        step_state.value = (step_state.value + dir) % 8

        with self.newlock:
            mask = ~(0b1111 << self.shifter_bit_start)
            Stepper.shifter_outputs.value &= mask
            Stepper.shifter_outputs.value |= Stepper.seq[step_state.value] << self.shifter_bit_start
            self.s.shiftByte(Stepper.shifter_outputs.value)

        angle.value = (angle.value + dir / Stepper.steps_per_degree) % 360

    def __rotate(self, delta, angle, step_state, busy_flag):
        with self.lock:
            busy_flag.value = 1

            numSteps = int(abs(delta) * Stepper.steps_per_degree)
            direction = self.__sgn(delta)

            for _ in range(numSteps):
                self.__step(direction, angle, step_state)
                time.sleep(Stepper.delay / 1e6)

            busy_flag.value = 0

    def rotate(self, delta):
        if self.busy.value == 1:
            return

        p = multiprocessing.Process(
            target=self.__rotate,
            args=(delta, self.angle, self.step_state, self.busy)
        )
        p.start()

    def goAngle(self, angle):
        if self.busy.value == 1:
            return

        diff = angle - self.angle.value
        move = (diff + 180) % 360 - 180

        p = multiprocessing.Process(
            target=self.__rotate,
            args=(move, self.angle, self.step_state, self.busy)
        )
        p.start()

    def zero(self):
        self.angle.value = 0
        self.step_state.value = 0



# Example use:

if __name__ == '__main__':

    s = Shifter(data=16,latch=20,clock=21)   # set up Shifter

    # Use multiprocessing.Lock() to prevent motors from trying to 
    # execute multiple operations at the same time:
    newlock = multiprocessing.Lock()
    lock1 = multiprocessing.Lock()
    lock2 = multiprocessing.Lock()

    # Instantiate 2 Steppers:
    m1 = Stepper(s, lock1, newlock)
    m2 = Stepper(s, lock2, newlock)


    m1.zero()
    m2.zero()
    m1.goAngle(90)
    m1.goAngle(-45)
    m2.goAngle(-90)
    m2.goAngle(45)
    m1.goAngle(-135)
    m1.goAngle(135)
    m1.goAngle(0)
 
    # While the motors are running in their separate processes, the main
    # code can continue doing its thing: 
    try:
        while True:
            pass
    except:
        print('\nend')