#include <uwebsockets/App.h>
#include <iostream>
#include <thread>
#include <chrono>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

// Custom user data struct for WebSocket
struct PerSocketData {};

void sendTestData(uWS::WebSocket<false, true, PerSocketData>* ws) {
    std::vector<std::string> node_ids = {
        "Rt_", "Rt_F", "Rt_FL", "Rt_FR", "Rt_FRF", "Rt_FRFL", "Rt_FRFR"
    };

    for (size_t i = 0; i < node_ids.size(); ++i) {
        json data = {
            {"node_id", node_ids[i]},
            {"current_direction", "F"},
            {"distance", 42},
            {"return", false}
        };

        std::string message = data.dump();
        ws->send(message, uWS::OpCode::TEXT);
        std::this_thread::sleep_for(std::chrono::milliseconds(1000));
    }
}

int main() {
    std::cout << "[INFO] Starting C++ WebSocket test server on ws://localhost:8765\n";

    uWS::App()
    .ws<PerSocketData>("/*", {
        .open = [](uWS::WebSocket<false, true, PerSocketData>* ws) {
            std::cout << "[SERVER] Client connected\n";
            std::thread(sendTestData, ws).detach();
        },
        .message = [](uWS::WebSocket<false, true, PerSocketData>* ws, std::string_view msg, uWS::OpCode) {
            std::cout << "[SERVER] Received: " << msg << "\n";
        },
        .close = [](uWS::WebSocket<false, true, PerSocketData>* ws, int /*code*/, std::string_view /*msg*/) {
            std::cout << "[SERVER] Connection closed\n";
        }
    })
    .listen(8765, [](auto* token) {
        if (token) {
            std::cout << "[INFO] Server listening on port 8765\n";
        } else {
            std::cerr << "[ERROR] Failed to start server\n";
        }
    }).run();

    return 0;
}
