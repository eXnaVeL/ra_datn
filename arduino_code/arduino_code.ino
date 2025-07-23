// CNC_Firmware_Accel.ino

#include <AccelStepper.h>
#include <MultiStepper.h>
#include "CNCLogic.h"

// --- KHAI BÁO CÁC ĐỐI TƯỢNG STEPPER ---
// Chế độ DRIVER (1) sử dụng 2 chân: step và direction.
// Các chân này phải khớp với các hằng số trong file logic.
AccelStepper stepperX(AccelStepper::DRIVER, stepX, dirX);
AccelStepper stepperY(AccelStepper::DRIVER, stepY, dirY);
AccelStepper stepperZ(AccelStepper::DRIVER, stepZ, dirZ);

// Tạo một đối tượng MultiStepper để điều khiển đồng bộ
MultiStepper steppers;

void setup() {
  Serial.begin(9600);
  
  // Thiết lập các chân (enable, limit switches)
  setupPins();

  // Thiết lập các thông số ban đầu cho stepper (tốc độ, gia tốc)
  setupSteppers();

  // Thêm các stepper vào bộ điều khiển đa trục
  steppers.addStepper(stepperX);
  steppers.addStepper(stepperY);
  steppers.addStepper(stepperZ);
}

void loop() {
  // Xử lý các lệnh đến từ Serial
  if (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '!') {
      handleInterrupt();
    } else if (c == '\n') {
      command_buffer.trim();
      if (command_buffer.length() > 0) {
        processCommand(command_buffer);
      }
      command_buffer = "";
    } else {
      command_buffer += c;
    }
  }

  // Luôn chạy các bộ điều khiển stepper
  // Đây là trái tim của AccelStepper, nó xử lý việc tạo xung không chặn
  if (currentMachineState == MOVING) {
    // steppers.run() trả về true nếu vẫn đang di chuyển, false nếu đã hoàn tất.
    if (!steppers.run()) {
      currentMachineState = IDLE;
      Serial.println("Move complete. OK");
    }
  } else if (currentMachineState == HOMING) {
    // Động cơ homing sẽ được chạy bởi runHomingEngine()
    runHomingEngine();
  }
}