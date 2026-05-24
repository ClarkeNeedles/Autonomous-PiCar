#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/bool.hpp"
#include "std_msgs/msg/string.hpp"
#include "geometry_msgs/msg/pose2_d.hpp"
#include "nav_msgs/msg/odometry.hpp"

#include <cmath>
#include <chrono>
#include <string>

#include <regex>

class BehaviorManagerNode : public rclcpp::Node
{
public:
    BehaviorManagerNode()
    : Node("behavior_manager_node"),
      obstacle_active_(false),
      obstacle_hold_active_(false),
      frame_counter_(0),
      have_current_pose_(false),
      have_target_pose_(false),
      fare_phase_(NO_FARE),
      have_pickup_pose_(false),
      have_dropoff_pose_(false),
      pickup_reached_(false),
      dropoff_reached_(false),
      fare_in_position_(false),
      fare_picked_up_(false),
      fare_completed_(false),
      active_fare_id_(-1),
      ultrasonic_state_label_("CLEAR")
    {
        // ---- Parameters ----
        this->declare_parameter("pickup_reached_threshold_cm", 25.0);
        this->declare_parameter("dropoff_reached_threshold_cm", 25.0);
        this->declare_parameter("ultrasonic_wait_sec", 3.0);
        this->declare_parameter("fare_wait_timeout_sec", 45.0);

        pickup_reached_threshold_cm_ =
            this->get_parameter("pickup_reached_threshold_cm").as_double();
        dropoff_reached_threshold_cm_ =
            this->get_parameter("dropoff_reached_threshold_cm").as_double();
        ultrasonic_wait_sec_ =
            this->get_parameter("ultrasonic_wait_sec").as_double();
        fare_wait_timeout_sec_ =
            this->get_parameter("fare_wait_timeout_sec").as_double();

        fare_wait_entered_ = this->now();

        // ---- Subscribers ----
        ultrasonic_sub_ = this->create_subscription<std_msgs::msg::Bool>(
            "/ultrasonic/detected",
            10,
            std::bind(&BehaviorManagerNode::ultrasonicCallback, this, std::placeholders::_1)
        );

        odom_sub_ = this->create_subscription<nav_msgs::msg::Odometry>(
            "/odometry/filtered",
            10,
            std::bind(&BehaviorManagerNode::odometryCallback, this, std::placeholders::_1)
        );

        current_fare_sub_ = this->create_subscription<std_msgs::msg::String>(
            "/vpfs/current_fare",
            10,
            std::bind(&BehaviorManagerNode::currentFareCallback, this, std::placeholders::_1)
        );

        // ---- Publishers ----
        driving_allowed_pub_ =
            this->create_publisher<std_msgs::msg::Bool>("/autonomy/driving_allowed", 10);
        current_pose_pub_ =
            this->create_publisher<geometry_msgs::msg::Pose2D>("/navigation/current_pose", 10);
        target_pose_pub_ =
            this->create_publisher<geometry_msgs::msg::Pose2D>("/navigation/target_pose", 10);

        // ---- Timer ----
        timer_ = this->create_wall_timer(
            std::chrono::milliseconds(50),
            std::bind(&BehaviorManagerNode::onTimer, this)
        );

        RCLCPP_INFO(
            this->get_logger(),
            "Behavior manager ready | ultrasonic_wait=%.2f fare_timeout=%.2f",
            ultrasonic_wait_sec_, fare_wait_timeout_sec_);
    }

private:
    enum FarePhase
    {
        NO_FARE = 0,
        GO_TO_PICKUP = 1,
        WAIT_FOR_PICKUP_POSITION = 2,
        WAIT_FOR_PICKUP_CONFIRM = 3,
        GO_TO_DROPOFF = 4,
        WAIT_FOR_DROPOFF_POSITION = 5,
        WAIT_FOR_DROPOFF_CONFIRM = 6
    };

    void ultrasonicCallback(const std_msgs::msg::Bool::SharedPtr msg)
    {
        const bool previous_obstacle = obstacle_active_;
        obstacle_active_ = msg->data;

        // Only log on state change to avoid 10 Hz spam
        if (obstacle_active_ != previous_obstacle) {
            RCLCPP_INFO(
                this->get_logger(),
                "[ULTRASONIC] state=%s detected=%d->%d hold=%d",
                ultrasonic_state_label_.c_str(),
                previous_obstacle ? 1 : 0,
                obstacle_active_ ? 1 : 0,
                obstacle_hold_active_ ? 1 : 0);
        }

        if (!obstacle_hold_active_ && !previous_obstacle && obstacle_active_) {
            startUltrasonicHold("ULTRASONIC_DETECTED");
        }
    }

    void odometryCallback(const nav_msgs::msg::Odometry::SharedPtr msg)
    {
        const auto & p = msg->pose.pose.position;
        const auto & q = msg->pose.pose.orientation;

        current_pose_.x = p.x;
        current_pose_.y = p.y;
        current_pose_.theta = yawFromQuaternion(q.x, q.y, q.z, q.w);
        have_current_pose_ = true;

        current_pose_pub_->publish(current_pose_);
    }

    void currentFareCallback(const std_msgs::msg::String::SharedPtr msg)
    {
        FarePhase parsed_phase = NO_FARE;
        geometry_msgs::msg::Pose2D pickup;
        geometry_msgs::msg::Pose2D dropoff;
        int fare_id = -1;
        bool in_position = false;
        bool picked_up = false;
        bool completed = false;

        if (!parseFareJson(
                msg->data,
                parsed_phase,
                fare_id,
                pickup,
                dropoff,
                in_position,
                picked_up,
                completed))
        {
            RCLCPP_WARN_THROTTLE(
                this->get_logger(),
                *this->get_clock(),
                3000,
                "Could not parse /vpfs/current_fare JSON");
            return;
        }

        if (parsed_phase == NO_FARE) {
            clearFareState();
            return;
        }

        fare_in_position_ = in_position;
        fare_picked_up_ = picked_up;
        fare_completed_ = completed;

        const bool is_new_fare = (fare_id != active_fare_id_);

        if (is_new_fare) {
            active_fare_id_ = fare_id;
            pickup_pose_ = pickup;
            dropoff_pose_ = dropoff;
            have_pickup_pose_ = true;
            have_dropoff_pose_ = true;
            pickup_reached_ = false;
            dropoff_reached_ = false;

            fare_phase_ = GO_TO_PICKUP;

            RCLCPP_INFO(
                this->get_logger(),
                "New fare received | id=%d | pickup=(%.2f, %.2f) dropoff=(%.2f, %.2f)",
                active_fare_id_,
                pickup_pose_.x, pickup_pose_.y,
                dropoff_pose_.x, dropoff_pose_.y);

            updatePlannerTargetForFarePhase();
            return;
        }

        if (fare_phase_ == WAIT_FOR_PICKUP_POSITION && fare_in_position_) {
            fare_phase_ = WAIT_FOR_PICKUP_CONFIRM;
            fare_wait_entered_ = this->now();
            RCLCPP_INFO(this->get_logger(), "At pickup position. Waiting for pickedUp=true.");
        }

        if (fare_phase_ == WAIT_FOR_PICKUP_CONFIRM && fare_picked_up_) {
            fare_phase_ = GO_TO_DROPOFF;
            RCLCPP_INFO(this->get_logger(), "Pickup confirmed. Switching target to dropoff.");
            updatePlannerTargetForFarePhase();
        }

        if (fare_phase_ == WAIT_FOR_DROPOFF_POSITION && fare_in_position_) {
            fare_phase_ = WAIT_FOR_DROPOFF_CONFIRM;
            fare_wait_entered_ = this->now();
            RCLCPP_INFO(this->get_logger(), "At dropoff position. Waiting for completed=true.");
        }

        if (fare_phase_ == WAIT_FOR_DROPOFF_CONFIRM && fare_completed_) {
            RCLCPP_INFO(this->get_logger(), "Fare %d completed.", active_fare_id_);
            clearFareState();
        }
    }

    void onTimer()
    {
        if (have_current_pose_) {
            current_pose_pub_->publish(current_pose_);
        }

        updateFareProgress();

        if (have_target_pose_) {
            target_pose_pub_->publish(target_pose_);
        }

        if (obstacle_hold_active_) {
            handleUltrasonicHold();
        }

        const bool in_wait_state = (
            fare_phase_ == WAIT_FOR_PICKUP_POSITION ||
            fare_phase_ == WAIT_FOR_PICKUP_CONFIRM  ||
            fare_phase_ == WAIT_FOR_DROPOFF_POSITION ||
            fare_phase_ == WAIT_FOR_DROPOFF_CONFIRM
        );
        const bool driving = !obstacle_active_ && !obstacle_hold_active_ && !in_wait_state;

        auto allowed_msg = std_msgs::msg::Bool();
        allowed_msg.data = driving;
        driving_allowed_pub_->publish(allowed_msg);

        logDebug(driving);
    }

    void updateFareProgress()
    {
        if (!have_current_pose_) {
            return;
        }

        if (fare_phase_ == GO_TO_PICKUP && have_pickup_pose_) {
            const double d = planarDistance(current_pose_, pickup_pose_);
            if (d <= pickup_reached_threshold_cm_) {
                pickup_reached_ = true;
                fare_phase_ = WAIT_FOR_PICKUP_POSITION;
                fare_wait_entered_ = this->now();
                RCLCPP_INFO(
                    this->get_logger(),
                    "Near pickup for fare %d. Waiting for inPosition=true.",
                    active_fare_id_);
            }
        } else if (fare_phase_ == GO_TO_DROPOFF && have_dropoff_pose_) {
            const double d = planarDistance(current_pose_, dropoff_pose_);
            if (d <= dropoff_reached_threshold_cm_) {
                dropoff_reached_ = true;
                fare_phase_ = WAIT_FOR_DROPOFF_POSITION;
                fare_wait_entered_ = this->now();
                RCLCPP_INFO(
                    this->get_logger(),
                    "Near dropoff for fare %d. Waiting for inPosition=true.",
                    active_fare_id_);
            }
        }

        // Timeout: if stuck in any WAIT state, abandon the fare so we can
        // claim another and not stall indefinitely.
        if (fare_phase_ == WAIT_FOR_PICKUP_POSITION ||
            fare_phase_ == WAIT_FOR_PICKUP_CONFIRM  ||
            fare_phase_ == WAIT_FOR_DROPOFF_POSITION ||
            fare_phase_ == WAIT_FOR_DROPOFF_CONFIRM)
        {
            const double elapsed = (this->now() - fare_wait_entered_).seconds();
            if (elapsed > fare_wait_timeout_sec_) {
                RCLCPP_WARN(
                    this->get_logger(),
                    "WAIT timeout (%.1fs > %.1fs) for fare %d in phase %s — clearing.",
                    elapsed, fare_wait_timeout_sec_,
                    active_fare_id_, farePhaseToString().c_str());
                clearFareState();
            }
        }
    }

    void updatePlannerTargetForFarePhase()
    {
        have_target_pose_ = false;

        if (fare_phase_ == GO_TO_PICKUP && have_pickup_pose_) {
            target_pose_ = pickup_pose_;
            have_target_pose_ = true;
        } else if (fare_phase_ == GO_TO_DROPOFF && have_dropoff_pose_) {
            target_pose_ = dropoff_pose_;
            have_target_pose_ = true;
        }

        if (have_target_pose_) {
            target_pose_pub_->publish(target_pose_);
        }
    }

    void clearFareState()
    {
        fare_phase_ = NO_FARE;
        have_pickup_pose_ = false;
        have_dropoff_pose_ = false;
        have_target_pose_ = false;
        pickup_reached_ = false;
        dropoff_reached_ = false;
        fare_in_position_ = false;
        fare_picked_up_ = false;
        fare_completed_ = false;
        active_fare_id_ = -1;

        RCLCPP_INFO_THROTTLE(this->get_logger(), *this->get_clock(), 5000,
            "No active fare. Cleared fare navigation state.");
    }

    void startUltrasonicHold(const std::string & reason)
    {
        obstacle_hold_active_ = true;
        ultrasonic_hold_end_time_ =
            this->now() + rclcpp::Duration::from_seconds(ultrasonic_wait_sec_);
        ultrasonic_state_label_ = "WAITING";

        RCLCPP_WARN(
            this->get_logger(),
            "[ULTRASONIC] state=%s | reason=%s | detected=%d | wait=%.2f sec",
            ultrasonic_state_label_.c_str(),
            reason.c_str(),
            obstacle_active_ ? 1 : 0,
            ultrasonic_wait_sec_);
    }

    void handleUltrasonicHold()
    {
        if (this->now() < ultrasonic_hold_end_time_) {
            return;
        }

        if (obstacle_active_) {
            ultrasonic_state_label_ = "RECHECK_BLOCKED";
            RCLCPP_WARN(
                this->get_logger(),
                "[ULTRASONIC] state=%s | object still detected | waiting another %.2f sec",
                ultrasonic_state_label_.c_str(),
                ultrasonic_wait_sec_);
            ultrasonic_hold_end_time_ =
                this->now() + rclcpp::Duration::from_seconds(ultrasonic_wait_sec_);
            ultrasonic_state_label_ = "WAITING";
            return;
        }

        obstacle_hold_active_ = false;
        ultrasonic_state_label_ = "CLEAR";
        RCLCPP_INFO(
            this->get_logger(),
            "[ULTRASONIC] state=%s | object cleared | resuming",
            ultrasonic_state_label_.c_str());
    }

    bool parseFareJson(
        const std::string & json_text,
        FarePhase & phase_out,
        int & fare_id_out,
        geometry_msgs::msg::Pose2D & pickup_out,
        geometry_msgs::msg::Pose2D & dropoff_out,
        bool & in_position_out,
        bool & picked_up_out,
        bool & completed_out)
    {
        const auto extract_string = [&](const std::string & key, std::string & value) -> bool {
            const std::regex pattern("\"" + key + R"(\"\s*:\s*\"([^\"]+)\")");
            std::smatch match;
            if (!std::regex_search(json_text, match, pattern)) {
                return false;
            }
            value = match[1].str();
            return true;
        };

        const auto extract_int = [&](const std::string & key, int & value) -> bool {
            const std::regex pattern("\"" + key + R"(\"\s*:\s*(-?\d+))");
            std::smatch match;
            if (!std::regex_search(json_text, match, pattern)) {
                return false;
            }
            value = std::stoi(match[1].str());
            return true;
        };

        const auto extract_bool = [&](const std::string & key, bool & value) -> bool {
            const std::regex pattern("\"" + key + R"(\"\s*:\s*(true|false))");
            std::smatch match;
            if (!std::regex_search(json_text, match, pattern)) {
                return false;
            }
            value = (match[1].str() == "true");
            return true;
        };

        const auto extract_pose = [&](const std::string & key, geometry_msgs::msg::Pose2D & pose) -> bool {
            const std::regex pattern(
                "\"" + key + R"(\"\s*:\s*\{[^\}]*\"x\"\s*:\s*(-?\d+(?:\.\d+)?)\s*,\s*\"y\"\s*:\s*(-?\d+(?:\.\d+)?)\s*)"
                R"([^\}]*\})");
            std::smatch match;
            if (!std::regex_search(json_text, match, pattern)) {
                return false;
            }
            pose.x = std::stod(match[1].str());
            pose.y = std::stod(match[2].str());
            pose.theta = 0.0;
            return true;
        };

        try {
            std::string status;
            if (!extract_string("status", status)) {
                return false;
            }

            if (status != "active") {
                phase_out = NO_FARE;
                fare_id_out = -1;
                in_position_out = false;
                picked_up_out = false;
                completed_out = false;
                return true;
            }

            if (!extract_int("id", fare_id_out)) {
                return false;
            }
            if (!extract_pose("src", pickup_out)) {
                return false;
            }
            if (!extract_pose("dest", dropoff_out)) {
                return false;
            }

            if (!extract_bool("inPosition", in_position_out)) {
                in_position_out = false;
            }
            if (!extract_bool("pickedUp", picked_up_out)) {
                picked_up_out = false;
            }
            if (!extract_bool("completed", completed_out)) {
                completed_out = false;
            }

            phase_out = GO_TO_PICKUP;
            return true;
        } catch (const std::exception & e) {
            RCLCPP_WARN(this->get_logger(), "JSON parse error: %s", e.what());
            return false;
        }
    }

    double yawFromQuaternion(double x, double y, double z, double w) const
    {
        const double siny_cosp = 2.0 * ((w * z) + (x * y));
        const double cosy_cosp = 1.0 - 2.0 * ((y * y) + (z * z));
        return std::atan2(siny_cosp, cosy_cosp);
    }

    double planarDistance(
        const geometry_msgs::msg::Pose2D & a,
        const geometry_msgs::msg::Pose2D & b) const
    {
        return std::hypot(b.x - a.x, b.y - a.y);
    }

    std::string farePhaseToString() const
    {
        switch (fare_phase_) {
            case GO_TO_PICKUP:
                return "GO_TO_PICKUP";
            case WAIT_FOR_PICKUP_POSITION:
                return "WAIT_FOR_PICKUP_POSITION";
            case WAIT_FOR_PICKUP_CONFIRM:
                return "WAIT_FOR_PICKUP_CONFIRM";
            case GO_TO_DROPOFF:
                return "GO_TO_DROPOFF";
            case WAIT_FOR_DROPOFF_POSITION:
                return "WAIT_FOR_DROPOFF_POSITION";
            case WAIT_FOR_DROPOFF_CONFIRM:
                return "WAIT_FOR_DROPOFF_CONFIRM";
            default:
                return "LINE_FOLLOW";
        }
    }

    void logDebug(bool driving_allowed)
    {
        frame_counter_++;
        if (frame_counter_ % 30 == 0) {
            RCLCPP_INFO(
                this->get_logger(),
                "[%s] driving_allowed=%d obstacle=%d hold=%d fare_phase=%d target=(%.2f, %.2f) ultrasonic=%s",
                farePhaseToString().c_str(),
                driving_allowed ? 1 : 0,
                obstacle_active_ ? 1 : 0,
                obstacle_hold_active_ ? 1 : 0,
                static_cast<int>(fare_phase_),
                have_target_pose_ ? target_pose_.x : -1.0,
                have_target_pose_ ? target_pose_.y : -1.0,
                ultrasonic_state_label_.c_str());
        }
    }

    // ---- Parameters ----
    double pickup_reached_threshold_cm_;
    double dropoff_reached_threshold_cm_;
    double ultrasonic_wait_sec_;
    double fare_wait_timeout_sec_;

    // ---- State ----
    bool obstacle_active_;
    bool obstacle_hold_active_;
    int frame_counter_;

    // Planner interface state
    geometry_msgs::msg::Pose2D current_pose_;
    geometry_msgs::msg::Pose2D target_pose_;
    bool have_current_pose_;
    bool have_target_pose_;

    // Fare navigation state
    rclcpp::Time fare_wait_entered_;
    FarePhase fare_phase_;
    geometry_msgs::msg::Pose2D pickup_pose_;
    geometry_msgs::msg::Pose2D dropoff_pose_;
    bool have_pickup_pose_;
    bool have_dropoff_pose_;
    bool pickup_reached_;
    bool dropoff_reached_;
    bool fare_in_position_;
    bool fare_picked_up_;
    bool fare_completed_;
    int active_fare_id_;

    rclcpp::Time ultrasonic_hold_end_time_;
    std::string ultrasonic_state_label_;

    // ---- ROS ----
    rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr ultrasonic_sub_;
    rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr odom_sub_;
    rclcpp::Subscription<std_msgs::msg::String>::SharedPtr current_fare_sub_;

    rclcpp::Publisher<std_msgs::msg::Bool>::SharedPtr driving_allowed_pub_;
    rclcpp::Publisher<geometry_msgs::msg::Pose2D>::SharedPtr current_pose_pub_;
    rclcpp::Publisher<geometry_msgs::msg::Pose2D>::SharedPtr target_pose_pub_;

    rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char * argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<BehaviorManagerNode>());
    rclcpp::shutdown();
    return 0;
}
