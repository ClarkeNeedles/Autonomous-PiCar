#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/float32.hpp"
#include <string>

class LaneFusionNode : public rclcpp::Node
{
public:
    LaneFusionNode() : Node("lane_fusion_node")
    {
        vision_offset_sub_ = this->create_subscription<std_msgs::msg::Float32>(
            "/vision_lane/offset", 10,
            std::bind(&LaneFusionNode::visionOffsetCallback, this, std::placeholders::_1));

        vision_conf_sub_ = this->create_subscription<std_msgs::msg::Float32>(
            "/vision_lane/confidence", 10,
            std::bind(&LaneFusionNode::visionConfCallback, this, std::placeholders::_1));

        grayscale_offset_sub_ = this->create_subscription<std_msgs::msg::Float32>(
            "/grayscale_lane/lateral_offset", 10,
            std::bind(&LaneFusionNode::grayscaleOffsetCallback, this, std::placeholders::_1));

        grayscale_conf_sub_ = this->create_subscription<std_msgs::msg::Float32>(
            "/grayscale_lane/confidence", 10,
            std::bind(&LaneFusionNode::grayscaleConfCallback, this, std::placeholders::_1));

        offset_pub_ = this->create_publisher<std_msgs::msg::Float32>("/lane_state/offset", 10);
        conf_pub_ = this->create_publisher<std_msgs::msg::Float32>("/lane_state/confidence", 10);

        timer_ = this->create_wall_timer(
            std::chrono::milliseconds(50),
            std::bind(&LaneFusionNode::update, this));

        RCLCPP_INFO(this->get_logger(), "lane_fusion_node started");
    }

private:
    enum FusionState
    {
        USE_VISION,
        USE_GRAYSCALE,
        BLEND,
        LOST
    };

    void visionOffsetCallback(const std_msgs::msg::Float32::SharedPtr msg)
    {
        vision_offset_ = msg->data;
    }

    void visionConfCallback(const std_msgs::msg::Float32::SharedPtr msg)
    {
        vision_conf_ = msg->data;
    }

    void grayscaleOffsetCallback(const std_msgs::msg::Float32::SharedPtr msg)
    {
        grayscale_offset_ = msg->data;
    }

    void grayscaleConfCallback(const std_msgs::msg::Float32::SharedPtr msg)
    {
        grayscale_conf_ = msg->data;
    }

    void update()
    {
        const float vision_good = 0.6f;
        const float grayscale_good = 0.6f;
        const float min_any = 0.2f;

        float fused_offset = 0.0f;
        float fused_conf = 0.0f;
        FusionState state = LOST;

        if (vision_conf_ > vision_good && grayscale_conf_ > grayscale_good)
            state = BLEND;
        else if (vision_conf_ > grayscale_conf_ && vision_conf_ > min_any)
            state = USE_VISION;
        else if (grayscale_conf_ >= vision_conf_ && grayscale_conf_ > min_any)
            state = USE_GRAYSCALE;

        switch (state)
        {
        case BLEND:
        {
            float total = vision_conf_ + grayscale_conf_;
            fused_offset = (vision_offset_ * vision_conf_ + grayscale_offset_ * grayscale_conf_) / total;
            fused_conf = std::max(vision_conf_, grayscale_conf_);
        }
        case USE_VISION:
        {
            fused_offset = vision_offset_;
            fused_conf = vision_conf_;
        }
        case USE_GRAYSCALE:
        {
            fused_offset = grayscale_offset_;
            fused_conf = grayscale_conf_;
        }
        default:
        {
            state = LOST;
            fused_offset = 0.0f;
            fused_conf = 0.0f;
        }
        }

        std_msgs::msg::Float32 offset_msg;
        offset_msg.data = fused_offset;
        offset_pub_->publish(offset_msg);

        std_msgs::msg::Float32 conf_msg;
        conf_msg.data = fused_conf;
        conf_pub_->publish(conf_msg);

        (void)state;
    }

    rclcpp::Subscription<std_msgs::msg::Float32>::SharedPtr vision_offset_sub_;
    rclcpp::Subscription<std_msgs::msg::Float32>::SharedPtr vision_conf_sub_;
    rclcpp::Subscription<std_msgs::msg::Float32>::SharedPtr grayscale_offset_sub_;
    rclcpp::Subscription<std_msgs::msg::Float32>::SharedPtr grayscale_conf_sub_;

    rclcpp::Publisher<std_msgs::msg::Float32>::SharedPtr offset_pub_;
    rclcpp::Publisher<std_msgs::msg::Float32>::SharedPtr conf_pub_;

    rclcpp::TimerBase::SharedPtr timer_;

    float vision_offset_ = 0.0f;
    float vision_conf_ = 0.0f;
    float grayscale_offset_ = 0.0f;
    float grayscale_conf_ = 0.0f;
};

int main(int argc, char * argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<LaneFusionNode>());
    rclcpp::shutdown();
    return 0;
}