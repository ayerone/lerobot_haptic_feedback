
#include <SimpleFOC.h>

const int BAUD = 9600;

const int MOTOR_1  =  9;
const int MOTOR_2  = 10;
const int MOTOR_3  = 11;
const int MOTOR_EN =  8;

const int SUPPLY_VOLTAGE = 12;
const float VOLTAGE_LIMIT = 4;
const float CURRENT_LIMIT = 1;

float torque_setting = 0;

// Initialize the I2C sensor (AS5600)
MagneticSensorI2C encoder = MagneticSensorI2C(AS5600_I2C);
BLDCMotor motor = BLDCMotor(7);
BLDCDriver3PWM driver = BLDCDriver3PWM(MOTOR_1, MOTOR_2, MOTOR_3, MOTOR_EN);

void setup() {
  
  Serial.begin(BAUD);
  
  encoder.init();
  motor.linkSensor(&encoder);

  driver.voltage_power_supply = SUPPLY_VOLTAGE;
  driver.init();
  motor.linkDriver(&driver);

  motor.torque_controller = TorqueControlType::estimated_current;
  motor.controller = MotionControlType::torque;

  motor.phase_resistance = 2.3;
  motor.KV_rating = 220;
  // motor.axis_inductance.q = 0.01; // ex. 10 mH

  motor.updateVoltageLimit(VOLTAGE_LIMIT);
  motor.updateCurrentLimit(1.2);

  // motor.LPF_velocity.Tf = 0.05;
  // motor.LPF_angle.Tf = 0.005;

  motor.init();
  motor.initFOC();

  Serial.println("Hello");

}

void loop() {
  motor.loopFOC();

  // motor.move(- 0.125 * motor.shaftVelocity());
  
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim(); // Remove any whitespace or \r

    if (command == "READ") {
      Serial.println(motor.shaftAngle());
    } else if (command == "DISABLE") {
      Serial.println("DISABLED");
      motor.disable();
    } else if (command == "ENABLE") {
      Serial.println("ENABLED");
      motor.enable();
    } else {
      torque_setting = command.toFloat();
      motor.move(torque_setting);
      // target_set = true;
      // Serial.println("ok");
      // Serial.print("target ");
      // sprintf(out_buffer, "set target: %s", command);
      // Serial.println(target_angle);
      Serial.println("set " + String(torque_setting));
    }
  }
  
}