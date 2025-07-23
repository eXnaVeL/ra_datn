// CNCLogic_Accel.h


#ifndef CNCLOGIC_H
#define CNCLOGIC_H

#include <Arduino.h>

// --- KHAI BÁO CHÂN (Constants) ---
// Các hằng số này được định nghĩa trong file .ino chính
const int stepX = 2; const int dirX = 5;
const int stepY = 3; const int dirY = 6;
const int stepZ = 4; const int dirZ = 7;
const int enPin = 8;

const int X_LIMIT_PIN = 9;
const int Y_LIMIT_PIN = 10;
const int Z_LIMIT_PIN = 11;

const int HOMING_DIR_X =  1;
const int HOMING_DIR_Y = -1;
const int HOMING_DIR_Z =  1;

// --- KHAI BÁO CÁC ĐỐI TƯỢNG STEPPER TỪ FILE .ino ---
// Sử dụng 'extern' để cho trình biên dịch biết các đối tượng này tồn tại ở file khác
extern AccelStepper stepperX;
extern AccelStepper stepperY;
extern AccelStepper stepperZ;
extern MultiStepper steppers;

// ==========================================================
// CỖ MÁY TRẠNG THÁI TOÀN CỤC (GLOBAL STATE MACHINE)
// ==========================================================
enum MachineState {
  IDLE,
  HOMING,
  MOVING
};
MachineState currentMachineState = IDLE;

// --- BIẾN CHO HOMING (NON-BLOCKING) ---
enum HomingSubState {
  H_START, H_START_YZ, H_FAST_YZ, H_BACKOFF1_YZ, H_SLOW_YZ, H_BACKOFF2_YZ,
  H_START_X, H_FAST_X, H_BACKOFF1_X, H_SLOW_X, H_BACKOFF2_X,
  H_COMPLETE, H_STOPPED
};
HomingSubState currentHomingState = H_START;

const float homing_speed_fast = 1200.0; // steps/second
const float homing_speed_slow = 400.0;  // steps/second
const long backoff_steps = 200;
const long final_backoff_steps = 20;

bool y_homed_fast, z_homed_fast, y_homed_slow, z_homed_slow;

// --- BIẾN CHUNG ---
String command_buffer = "";
bool python_connected = false;

// --- KHAI BÁO HÀM ---
void setupPins();
void setupSteppers();
void handleInterrupt();
void processCommand(String command);
long findValue(String s, char c);
void setupMultiAxisMove_Accel(long stepsX, long stepsY, long stepsZ);
void runHomingEngine();

// --- ĐỊNH NGHĨA HÀM ---

void setupPins() {
  pinMode(enPin, OUTPUT);
  digitalWrite(enPin, LOW); // Mặc định bật động cơ (LOW = enabled)

  pinMode(X_LIMIT_PIN, INPUT_PULLUP);
  pinMode(Y_LIMIT_PIN, INPUT_PULLUP);
  pinMode(Z_LIMIT_PIN, INPUT_PULLUP);
}

void setupSteppers() {
  stepperX.setMaxSpeed(2000); // steps/second
  stepperX.setAcceleration(1000); // steps/second^2
  
  stepperY.setMaxSpeed(2000);
  stepperY.setAcceleration(1000);

  stepperZ.setMaxSpeed(1500);
  stepperZ.setAcceleration(800);
}

void handleInterrupt() {
  // Dừng tất cả các động cơ với giảm tốc
  stepperX.stop();
  stepperY.stop();
  stepperZ.stop();
  
  // Vòng lặp ngắn để thực hiện việc dừng
  while (stepperX.isRunning() || stepperY.isRunning() || stepperZ.isRunning()) {
    stepperX.run();
    stepperY.run();
    stepperZ.run();
  }

  if (currentMachineState == HOMING) {
    currentHomingState = H_STOPPED;
  }
  if (currentMachineState == MOVING) {
    currentMachineState = IDLE; // Trạng thái đã dừng
    Serial.println("Move stopped. OK");
  }
  
  while(Serial.available() > 0) Serial.read();
  command_buffer = "";
}

void processCommand(String command) {
  python_connected = true; 
  
  if (currentMachineState != IDLE && command.charAt(0) != 'E') {
    Serial.println("Error: Machine is busy. OK");
    return;
  }
  
  char cmd_char = command.charAt(0);
  switch (cmd_char) {
    case 'H':
      currentMachineState = HOMING;
      currentHomingState = H_START;
      break;
    case 'S': { // Thay đổi tốc độ
      unsigned int delay_us = command.substring(1).toInt();
      if (delay_us < 200) delay_us = 200;
      // Chuyển đổi từ delay (us) sang speed (steps/s)
      float speed = 1000000.0 / delay_us;
      stepperX.setMaxSpeed(speed);
      stepperY.setMaxSpeed(speed);
      stepperZ.setMaxSpeed(speed * 0.75); // Trục Z thường chậm hơn
      Serial.println("OK");
      break;
    }
    case 'E': // Enable/Disable motors
      if (command.substring(1).toInt() == 1) {
        digitalWrite(enPin, LOW);
      } else {
        digitalWrite(enPin, HIGH);
      }
      Serial.println("OK");
      break;
    case 'X':
    case 'Y':
    case 'Z': {
      char axis = command.charAt(0);
      long steps = command.substring(1).toInt();
      long sX = (axis == 'X') ? steps : 0;
      long sY = (axis == 'Y') ? steps : 0;
      long sZ = (axis == 'Z') ? steps : 0;
      setupMultiAxisMove_Accel(sX, sY, sZ);
      break;
    }
    case 'M': {
      long sX = findValue(command, 'X');
      long sY = findValue(command, 'Y');
      long sZ = findValue(command, 'Z');
      setupMultiAxisMove_Accel(sX, sY, sZ);
      break;
    }
    case '?': 
      Serial.println("Ready");
      break;
    default:
      python_connected = false; 
      Serial.println("Error: Unknown command. OK");
  }
}

long findValue(String s, char c) {
  int index = s.indexOf(c);
  if (index == -1) return 0;
  int endIndex = index + 1;
  while (endIndex < s.length() && (isDigit(s.charAt(endIndex)) || s.charAt(endIndex) == '-')) {
    endIndex++;
  }
  return s.substring(index + 1, endIndex).toInt();
}

void setupMultiAxisMove_Accel(long stepsX, long stepsY, long stepsZ) {
  if (stepsX == 0 && stepsY == 0 && stepsZ == 0) {
    Serial.println("OK");
    return;
  }

  currentMachineState = MOVING;
  Serial.println("Moving...");

  // AccelStepper hoạt động với tọa độ tuyệt đối,
  // vì vậy để thực hiện một di chuyển tương đối, chúng ta reset vị trí hiện tại về 0.
  stepperX.setCurrentPosition(0);
  stepperY.setCurrentPosition(0);
  stepperZ.setCurrentPosition(0);

  long positions[3] = {stepsX, stepsY, stepsZ};
  steppers.moveTo(positions);
}

void runHomingEngine() {
  switch (currentHomingState) {
    case H_START:
      Serial.println("Homing sequence started...");
      currentHomingState = H_START_YZ;
      break;

    case H_START_YZ:
      Serial.println("Homing Y and Z Axis...");
      y_homed_fast = false; z_homed_fast = false;
      y_homed_slow = false; z_homed_slow = false;
      // Đặt tốc độ và gia tốc cho homing nhanh
      stepperY.setMaxSpeed(homing_speed_fast);
      stepperZ.setMaxSpeed(homing_speed_fast);
      stepperY.setAcceleration(2000);
      stepperZ.setAcceleration(2000);
      currentHomingState = H_FAST_YZ;
      break;

    case H_FAST_YZ:
      // Di chuyển liên tục cho đến khi chạm công tắc
      if (!y_homed_fast) {
        if (digitalRead(Y_LIMIT_PIN) == LOW) y_homed_fast = true;
        else stepperY.setSpeed(homing_speed_fast * HOMING_DIR_Y);
      } else stepperY.setSpeed(0);
      
      if (!z_homed_fast) {
        if (digitalRead(Z_LIMIT_PIN) == LOW) z_homed_fast = true;
        else stepperZ.setSpeed(homing_speed_fast * HOMING_DIR_Z);
      } else stepperZ.setSpeed(0);

      stepperY.runSpeed();
      stepperZ.runSpeed();

      if (y_homed_fast && z_homed_fast) {
        stepperY.stop(); stepperZ.stop(); // Dừng lại
        stepperY.setCurrentPosition(0); stepperZ.setCurrentPosition(0);
        currentHomingState = H_BACKOFF1_YZ;
      }
      break;

    case H_BACKOFF1_YZ:
      // Lùi ra một khoảng cách cố định
      stepperY.moveTo(-HOMING_DIR_Y * backoff_steps);
      stepperZ.moveTo(-HOMING_DIR_Z * backoff_steps);
      
      stepperY.run();
      stepperZ.run();
      
      if (!stepperY.isRunning() && !stepperZ.isRunning()) {
        currentHomingState = H_SLOW_YZ;
      }
      break;

    case H_SLOW_YZ:
      // Đặt tốc độ chậm và di chuyển lại về phía công tắc
      stepperY.setMaxSpeed(homing_speed_slow);
      stepperZ.setMaxSpeed(homing_speed_slow);

      if (!y_homed_slow) {
        if (digitalRead(Y_LIMIT_PIN) == LOW) y_homed_slow = true;
        else stepperY.setSpeed(homing_speed_slow * HOMING_DIR_Y);
      } else stepperY.setSpeed(0);
      
      if (!z_homed_slow) {
        if (digitalRead(Z_LIMIT_PIN) == LOW) z_homed_slow = true;
        else stepperZ.setSpeed(homing_speed_slow * HOMING_DIR_Z);
      } else stepperZ.setSpeed(0);

      stepperY.runSpeed();
      stepperZ.runSpeed();

      if (y_homed_slow && z_homed_slow) {
        stepperY.stop(); stepperZ.stop();
        // Đây là điểm 0 chính xác
        stepperY.setCurrentPosition(0);
        stepperZ.setCurrentPosition(0);
        currentHomingState = H_BACKOFF2_YZ;
      }
      break;

    case H_BACKOFF2_YZ:
      // Lùi ra một khoảng nhỏ cuối cùng
      stepperY.moveTo(-HOMING_DIR_Y * final_backoff_steps);
      stepperZ.moveTo(-HOMING_DIR_Z * final_backoff_steps);
      
      stepperY.run();
      stepperZ.run();
      
      if (!stepperY.isRunning() && !stepperZ.isRunning()) {
        currentHomingState = H_START_X; // Bắt đầu homing trục X
      }
      break;

    // Các bước homing cho trục X tương tự Y/Z
    case H_START_X:
        Serial.println("Homing X-Axis...");
        stepperX.setMaxSpeed(homing_speed_fast);
        stepperX.setAcceleration(2000);
        currentHomingState = H_FAST_X;
        break;

    case H_FAST_X:
        if (digitalRead(X_LIMIT_PIN) == LOW) {
            stepperX.stop();
            stepperX.setCurrentPosition(0);
            currentHomingState = H_BACKOFF1_X;
        } else {
            stepperX.setSpeed(homing_speed_fast * HOMING_DIR_X);
            stepperX.runSpeed();
        }
        break;
        
    case H_BACKOFF1_X:
        stepperX.moveTo(-HOMING_DIR_X * backoff_steps);
        stepperX.run();
        if(!stepperX.isRunning()) currentHomingState = H_SLOW_X;
        break;
        
    case H_SLOW_X:
        stepperX.setMaxSpeed(homing_speed_slow);
        if (digitalRead(X_LIMIT_PIN) == LOW) {
            stepperX.stop();
            stepperX.setCurrentPosition(0); // Điểm 0 chính xác
            currentHomingState = H_BACKOFF2_X;
        } else {
            stepperX.setSpeed(homing_speed_slow * HOMING_DIR_X);
            stepperX.runSpeed();
        }
        break;

    case H_BACKOFF2_X:
        stepperX.moveTo(-HOMING_DIR_X * final_backoff_steps);
        stepperX.run();
        if(!stepperX.isRunning()) currentHomingState = H_COMPLETE;
        break;

    case H_COMPLETE:
      Serial.println("Homing complete. OK");
      setupSteppers(); // Reset tốc độ/gia tốc về giá trị mặc định
      currentMachineState = IDLE;
      break;
      
    case H_STOPPED:
      Serial.println("Homing stopped. OK");
      currentMachineState = IDLE;
      break;
  }
}

#endif // CNCLOGIC_ACCEL_H