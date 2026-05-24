#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/float32.hpp"

class PidNode : public rclcpp::Node
{
public:
    PidNode() : Node("pid_node")
    {
        this->declare_parameter("kp", 1.0);
        this->declare_parameter("ki", 0.0);
        this->declare_parameter("kd", 0.1);

        kp_ = this->get_parameter("kp").as_double();
        ki_ = this->get_parameter("ki").as_double();
        kd_ = this->get_parameter("kd").as_double();

        offset_sub_ = this->create_subscription<std_msgs::msg::Float32>(
            "/lane_state/offset", 10,
            std::bind(&PidNode::offsetCallback, this, std::placeholders::_1));

        conf_sub_ = this->create_subscription<std_msgs::msg::Float32>(
            "/lane_state/confidence", 10,
            std::bind(&PidNode::confCallback, this, std::placeholders::_1));

        steering_pub_ = this->create_publisher<std_msgs::msg::Float32>("/steering_cmd", 10);

        timer_ = this->create_wall_timer(
            std::chrono::milliseconds(50),
            std::bind(&PidNode::update, this));

        prev_time_ = this->now();

        RCLCPP_INFO(this->get_logger(), "lane_pid_node started");
    }

private:
    void offsetCallback(const std_msgs::msg::Float32::SharedPtr msg)
    {
        offset_ = msg->data;
    }

    void confCallback(const std_msgs::msg::Float32::SharedPtr msg)
    {
        confidence_ = msg->data;
    }

    void update()
    {
        if (confidence_ < 0.2f)
        {
            return;
        }

        rclcpp::Time now = this->now();
        double dt = (now - prev_time_).seconds();
        if (dt <= 0.0) {
            return;
        }

        double error = offset_;
        integral_ += error * dt;
        double derivative = (error - prev_error_) / dt;

        double output = kp_ * error + ki_ * integral_ + kd_ * derivative;

        if (output > 1.0) output = 1.0;
        if (output < -1.0) output = -1.0;

        std_msgs::msg::Float32 msg;
        msg.data = static_cast<float>(output);
        steering_pub_->publish(msg);

        prev_error_ = error;
        prev_time_ = now;
    }

    rclcpp::Subscription<std_msgs::msg::Float32>::SharedPtr offset_sub_;
    rclcpp::Subscription<std_msgs::msg::Float32>::SharedPtr conf_sub_;
    rclcpp::Publisher<std_msgs::msg::Float32>::SharedPtr steering_pub_;
    rclcpp::TimerBase::SharedPtr timer_;

    double kp_ = 1.0;
    double ki_ = 0.0;
    double kd_ = 0.1;

    double offset_ = 0.0;
    double confidence_ = 0.0;
    double prev_error_ = 0.0;
    double integral_ = 0.0;
    rclcpp::Time prev_time_;
};

int main(int argc, char * argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<PidNode>());
    rclcpp::shutdown();
    return 0;
}