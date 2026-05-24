#include <algorithm>
#include <cmath>
#include <deque>
#include <fstream>
#include <functional>
#include <limits>
#include <memory>
#include <queue>
#include <sstream>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

#include "geometry_msgs/msg/pose2_d.hpp"
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/int32_multi_array.hpp"
#include "std_msgs/msg/string.hpp"

namespace
{

constexpr double kPi = 3.14159265358979323846;

enum TurnCode
{
  LEFT = 0,
  STRAIGHT = 1,
  RIGHT = 2
};

struct MapNode
{
  std::string id;
  double x{};
  double y{};
  std::string label;
};

struct MapEdge
{
  std::string from;
  std::string to;
  double cost{};
};

struct PathResult
{
  bool found{false};
  double total_cost{0.0};
  std::vector<std::string> node_ids;
};

struct PoseState
{
  double x{};
  double y{};
  double heading_rad{};
  bool valid{false};
};

struct StartEdgeChoice
{
  bool found{false};
  std::string from;
  std::string to;
  double remaining_edge_cost{0.0};
  double score{std::numeric_limits<double>::max()};
  double distance_to_edge{std::numeric_limits<double>::max()};
  double heading_error_deg{180.0};
};

struct RoutePlan
{
  bool found{false};
  std::string goal_node;
  std::string next_node;
  std::vector<std::string> path_nodes;
  std::deque<int> turn_queue;
};

std::string trim(const std::string & value)
{
  const auto first = value.find_first_not_of(" \t\r\n");
  if (first == std::string::npos) {
    return "";
  }

  const auto last = value.find_last_not_of(" \t\r\n");
  return value.substr(first, last - first + 1);
}

std::vector<std::string> split_csv_line(const std::string & line)
{
  std::vector<std::string> fields;
  std::stringstream stream(line);
  std::string field;

  while (std::getline(stream, field, ',')) {
    fields.push_back(trim(field));
  }

  return fields;
}

double euclidean_distance(const MapNode & a, const MapNode & b)
{
  const double dx = a.x - b.x;
  const double dy = a.y - b.y;
  return std::sqrt((dx * dx) + (dy * dy));
}

double normalize_angle_rad(double angle)
{
  while (angle > kPi) {
    angle -= 2.0 * kPi;
  }

  while (angle < -kPi) {
    angle += 2.0 * kPi;
  }

  return angle;
}

double rad_to_deg(double angle_rad)
{
  return angle_rad * 180.0 / kPi;
}

std::string join_strings(const std::vector<std::string> & values, const std::string & separator)
{
  std::ostringstream stream;
  for (std::size_t i = 0; i < values.size(); ++i) {
    stream << values[i];
    if (i + 1 < values.size()) {
      stream << separator;
    }
  }

  return stream.str();
}

std::string join_turns(const std::deque<int> & turns)
{
  std::ostringstream stream;
  for (std::size_t i = 0; i < turns.size(); ++i) {
    stream << turns[i];
    if (i + 1 < turns.size()) {
      stream << ", ";
    }
  }

  return stream.str();
}

class RoadGraph
{
public:
  bool load_nodes_csv(const std::string & path, double coordinate_scale, rclcpp::Logger logger)
  {
    std::ifstream file(path);
    if (!file.is_open()) {
      RCLCPP_ERROR(logger, "Could not open node file: %s", path.c_str());
      return false;
    }

    nodes_.clear();
    adjacency_.clear();

    std::string line;
    std::size_t line_number = 0;
    while (std::getline(file, line)) {
      ++line_number;
      const std::string cleaned = trim(line);
      if (cleaned.empty() || cleaned[0] == '#') {
        continue;
      }

      const auto fields = split_csv_line(cleaned);
      if (fields.size() < 3) {
        RCLCPP_WARN(
          logger, "Skipping node line %zu because it has fewer than 3 columns", line_number);
        continue;
      }

      if (fields[0] == "id") {
        continue;
      }

      MapNode node;
      node.id = fields[0];
      node.x = std::stod(fields[1]) * coordinate_scale;
      node.y = std::stod(fields[2]) * coordinate_scale;
      node.label = fields.size() >= 4 ? fields[3] : fields[0];

      nodes_[node.id] = node;
      adjacency_[node.id] = {};
    }

    return !nodes_.empty();
  }

  bool load_edges_csv(const std::string & path, double coordinate_scale, rclcpp::Logger logger)
  {
    std::ifstream file(path);
    if (!file.is_open()) {
      RCLCPP_ERROR(logger, "Could not open edge file: %s", path.c_str());
      return false;
    }

    std::string line;
    std::size_t line_number = 0;
    while (std::getline(file, line)) {
      ++line_number;
      const std::string cleaned = trim(line);
      if (cleaned.empty() || cleaned[0] == '#') {
        continue;
      }

      const auto fields = split_csv_line(cleaned);
      if (fields.size() < 2) {
        RCLCPP_WARN(
          logger, "Skipping edge line %zu because it has fewer than 2 columns", line_number);
        continue;
      }

      if (fields[0] == "from") {
        continue;
      }

      const std::string & from = fields[0];
      const std::string & to = fields[1];

      if (nodes_.count(from) == 0 || nodes_.count(to) == 0) {
        RCLCPP_WARN(
          logger, "Skipping edge %s -> %s because one or both nodes do not exist",
          from.c_str(), to.c_str());
        continue;
      }

      double cost = 0.0;
      if (fields.size() >= 3 && !fields[2].empty()) {
        cost = std::stod(fields[2]) * coordinate_scale;
      } else {
        cost = euclidean_distance(nodes_.at(from), nodes_.at(to));
      }

      adjacency_[from].push_back(MapEdge{from, to, cost});
    }

    return true;
  }

  const MapNode * node(const std::string & node_id) const
  {
    const auto it = nodes_.find(node_id);
    if (it == nodes_.end()) {
      return nullptr;
    }

    return &it->second;
  }

  std::string nearest_node(double x, double y) const
  {
    double best_distance = std::numeric_limits<double>::max();
    std::string best_node_id;

    for (const auto & [node_id, map_node] : nodes_) {
      const double dx = map_node.x - x;
      const double dy = map_node.y - y;
      const double distance = std::sqrt((dx * dx) + (dy * dy));
      if (distance < best_distance) {
        best_distance = distance;
        best_node_id = node_id;
      }
    }

    return best_node_id;
  }

  PathResult shortest_path(const std::string & start, const std::string & goal) const
  {
    PathResult result;
    if (nodes_.count(start) == 0 || nodes_.count(goal) == 0) {
      return result;
    }

    using QueueEntry = std::pair<double, std::string>;
    std::priority_queue<QueueEntry, std::vector<QueueEntry>, std::greater<QueueEntry>> frontier;

    std::unordered_map<std::string, double> best_cost;
    std::unordered_map<std::string, std::string> previous;

    for (const auto & [node_id, _] : nodes_) {
      best_cost[node_id] = std::numeric_limits<double>::max();
    }

    best_cost[start] = 0.0;
    frontier.push({0.0, start});

    while (!frontier.empty()) {
      const auto [current_cost, current_id] = frontier.top();
      frontier.pop();

      if (current_cost > best_cost[current_id]) {
        continue;
      }

      if (current_id == goal) {
        break;
      }

      const auto adjacency_it = adjacency_.find(current_id);
      if (adjacency_it == adjacency_.end()) {
        continue;
      }

      for (const auto & edge : adjacency_it->second) {
        const double next_cost = current_cost + edge.cost;
        if (next_cost < best_cost[edge.to]) {
          best_cost[edge.to] = next_cost;
          previous[edge.to] = current_id;
          frontier.push({next_cost, edge.to});
        }
      }
    }

    if (best_cost[goal] == std::numeric_limits<double>::max()) {
      return result;
    }

    result.found = true;
    result.total_cost = best_cost[goal];

    for (std::string current = goal; !current.empty();) {
      result.node_ids.push_back(current);
      const auto prev_it = previous.find(current);
      if (prev_it == previous.end()) {
        break;
      }
      current = prev_it->second;
    }

    std::reverse(result.node_ids.begin(), result.node_ids.end());
    return result;
  }

  StartEdgeChoice choose_start_edge(
    const PoseState & pose,
    const std::string & goal_node,
    double max_snap_distance,
    double max_heading_error_deg) const
  {
    StartEdgeChoice best_choice;

    for (const auto & [from_id, edges] : adjacency_) {
      const MapNode & from_node = nodes_.at(from_id);
      for (const auto & edge : edges) {
        const MapNode & to_node = nodes_.at(edge.to);
        const double segment_dx = to_node.x - from_node.x;
        const double segment_dy = to_node.y - from_node.y;
        const double segment_length_sq = (segment_dx * segment_dx) + (segment_dy * segment_dy);
        if (segment_length_sq <= 0.0) {
          continue;
        }

        const double pose_dx = pose.x - from_node.x;
        const double pose_dy = pose.y - from_node.y;
        const double projection = ((pose_dx * segment_dx) + (pose_dy * segment_dy)) / segment_length_sq;
        const double clamped_projection = std::clamp(projection, 0.0, 1.0);

        const double closest_x = from_node.x + (clamped_projection * segment_dx);
        const double closest_y = from_node.y + (clamped_projection * segment_dy);
        const double distance_to_edge = std::sqrt(
          ((pose.x - closest_x) * (pose.x - closest_x)) +
          ((pose.y - closest_y) * (pose.y - closest_y)));

        if (distance_to_edge > max_snap_distance) {
          continue;
        }

        const double edge_heading = std::atan2(segment_dy, segment_dx);
        const double heading_error_deg = std::abs(
          rad_to_deg(normalize_angle_rad(edge_heading - pose.heading_rad)));
        if (heading_error_deg > max_heading_error_deg) {
          continue;
        }

        const auto remaining_path = shortest_path(edge.to, goal_node);
        if (!remaining_path.found) {
          continue;
        }

        const double remaining_edge_cost = edge.cost * (1.0 - clamped_projection);
        const double score =
          remaining_edge_cost +
          remaining_path.total_cost +
          (distance_to_edge * 2.0) +
          (heading_error_deg * 5.0);

        if (score < best_choice.score) {
          best_choice.found = true;
          best_choice.from = edge.from;
          best_choice.to = edge.to;
          best_choice.remaining_edge_cost = remaining_edge_cost;
          best_choice.score = score;
          best_choice.distance_to_edge = distance_to_edge;
          best_choice.heading_error_deg = heading_error_deg;
        }
      }
    }

    return best_choice;
  }

  std::deque<int> build_turn_queue(
    const std::vector<std::string> & full_path_nodes,
    double straight_threshold_deg) const
  {
    std::deque<int> turns;
    if (full_path_nodes.size() < 3) {
      return turns;
    }

    for (std::size_t i = 1; i + 1 < full_path_nodes.size(); ++i) {
      const MapNode * prev = node(full_path_nodes[i - 1]);
      const MapNode * current = node(full_path_nodes[i]);
      const MapNode * next = node(full_path_nodes[i + 1]);

      if (prev == nullptr || current == nullptr || next == nullptr) {
        continue;
      }

      turns.push_back(classify_turn(*prev, *current, *next, straight_threshold_deg));
    }

    return turns;
  }

  std::size_t node_count() const { return nodes_.size(); }

  std::size_t edge_count() const
  {
    std::size_t total = 0;
    for (const auto & [_, edges] : adjacency_) {
      total += edges.size();
    }
    return total;
  }

private:
  int classify_turn(
    const MapNode & from_node,
    const MapNode & at_node,
    const MapNode & to_node,
    double straight_threshold_deg) const
  {
    const double in_x = at_node.x - from_node.x;
    const double in_y = at_node.y - from_node.y;
    const double out_x = to_node.x - at_node.x;
    const double out_y = to_node.y - at_node.y;

    const double cross = (in_x * out_y) - (in_y * out_x);
    const double dot = (in_x * out_x) + (in_y * out_y);
    const double angle_deg = rad_to_deg(std::atan2(cross, dot));

    if (std::abs(angle_deg) <= straight_threshold_deg) {
      return STRAIGHT;
    }

    return angle_deg > 0.0 ? LEFT : RIGHT;
  }

  std::unordered_map<std::string, MapNode> nodes_;
  std::unordered_map<std::string, std::vector<MapEdge>> adjacency_;
};

class MapPlannerNode : public rclcpp::Node
{
public:
  MapPlannerNode()
  : Node("map_planner")
  {
    declare_parameter<std::string>("nodes_file", "src/navigation_pkg/config/map_nodes.csv");
    declare_parameter<std::string>("edges_file", "src/navigation_pkg/config/map_edges.csv");
    declare_parameter<double>("csv_unit_to_cm", 1.0);
    declare_parameter<double>("max_edge_snap_distance", 400.0);
    declare_parameter<double>("max_heading_error_deg", 60.0);
    declare_parameter<double>("straight_threshold_deg", 25.0);
    declare_parameter<bool>("use_initial_parameters", false);
    declare_parameter<double>("current_x", 0.0);
    declare_parameter<double>("current_y", 0.0);
    declare_parameter<double>("current_heading_deg", 0.0);
    declare_parameter<double>("target_x", 0.0);
    declare_parameter<double>("target_y", 0.0);

    const auto nodes_file = get_parameter("nodes_file").as_string();
    const auto edges_file = get_parameter("edges_file").as_string();
    const auto csv_unit_to_cm = get_parameter("csv_unit_to_cm").as_double();

    if (!graph_.load_nodes_csv(nodes_file, csv_unit_to_cm, get_logger())) {
      RCLCPP_ERROR(get_logger(), "Map planner failed to load nodes");
      return;
    }

    if (!graph_.load_edges_csv(edges_file, csv_unit_to_cm, get_logger())) {
      RCLCPP_ERROR(get_logger(), "Map planner failed to load edges");
      return;
    }

    max_edge_snap_distance_ = get_parameter("max_edge_snap_distance").as_double();
    max_heading_error_deg_ = get_parameter("max_heading_error_deg").as_double();
    straight_threshold_deg_ = get_parameter("straight_threshold_deg").as_double();

    next_node_pub_ = create_publisher<std_msgs::msg::String>("/navigation/next_node", 10);
    turn_queue_pub_ =
      create_publisher<std_msgs::msg::Int32MultiArray>("/navigation/turn_queue", 10);
    path_pub_ = create_publisher<std_msgs::msg::String>("/navigation/path_nodes", 10);

    current_pose_sub_ = create_subscription<geometry_msgs::msg::Pose2D>(
      "/navigation/current_pose", 10,
      std::bind(&MapPlannerNode::current_pose_callback, this, std::placeholders::_1));

    target_pose_sub_ = create_subscription<geometry_msgs::msg::Pose2D>(
      "/navigation/target_pose", 10,
      std::bind(&MapPlannerNode::target_pose_callback, this, std::placeholders::_1));

    RCLCPP_INFO(
      get_logger(),
      "Loaded graph with %zu nodes and %zu directed edges using csv_unit_to_cm=%.3f",
      graph_.node_count(), graph_.edge_count(), csv_unit_to_cm);

    if (get_parameter("use_initial_parameters").as_bool()) {
      current_pose_.x = get_parameter("current_x").as_double();
      current_pose_.y = get_parameter("current_y").as_double();
      current_pose_.heading_rad = normalize_angle_rad(
        get_parameter("current_heading_deg").as_double() * kPi / 180.0);
      current_pose_.valid = true;

      target_pose_.x = get_parameter("target_x").as_double();
      target_pose_.y = get_parameter("target_y").as_double();
      target_pose_.valid = true;

      try_plan();
    }
  }

private:
  void current_pose_callback(const geometry_msgs::msg::Pose2D::SharedPtr msg)
  {
    current_pose_.x = msg->x;
    current_pose_.y = msg->y;
    current_pose_.heading_rad = normalize_angle_rad(msg->theta);
    current_pose_.valid = true;
    try_plan();
  }

  void target_pose_callback(const geometry_msgs::msg::Pose2D::SharedPtr msg)
  {
    target_pose_.x = msg->x;
    target_pose_.y = msg->y;
    target_pose_.valid = true;
    try_plan();
  }

  void try_plan()
  {
    if (!current_pose_.valid || !target_pose_.valid) {
      return;
    }

    const std::string goal_node = graph_.nearest_node(target_pose_.x, target_pose_.y);
    if (goal_node.empty()) {
      RCLCPP_WARN(get_logger(), "Could not find a goal node for the target pose");
      return;
    }

    RoutePlan plan;
    plan.goal_node = goal_node;

    const auto start_edge = graph_.choose_start_edge(
      current_pose_, goal_node, max_edge_snap_distance_, max_heading_error_deg_);

    if (start_edge.found) {
      const auto remaining_path = graph_.shortest_path(start_edge.to, goal_node);
      if (!remaining_path.found) {
        RCLCPP_WARN(
          get_logger(), "No path found from inferred edge %s -> %s to goal %s",
          start_edge.from.c_str(), start_edge.to.c_str(), goal_node.c_str());
        return;
      }

      plan.found = true;
      plan.next_node = start_edge.to;
      plan.path_nodes.push_back(start_edge.from);
      plan.path_nodes.insert(
        plan.path_nodes.end(), remaining_path.node_ids.begin(), remaining_path.node_ids.end());
      plan.turn_queue = graph_.build_turn_queue(plan.path_nodes, straight_threshold_deg_);

      RCLCPP_INFO(
        get_logger(),
        "Start edge %s -> %s | edge_dist=%.1f heading_err=%.1f",
        start_edge.from.c_str(), start_edge.to.c_str(),
        start_edge.distance_to_edge, start_edge.heading_error_deg);
    } else {
      const std::string start_node = graph_.nearest_node(current_pose_.x, current_pose_.y);
      const auto path = graph_.shortest_path(start_node, goal_node);
      if (!path.found) {
        RCLCPP_WARN(
          get_logger(), "No path found from fallback start node %s to goal %s",
          start_node.c_str(), goal_node.c_str());
        return;
      }

      plan.found = true;
      plan.path_nodes = path.node_ids;
      if (plan.path_nodes.size() >= 2) {
        plan.next_node = plan.path_nodes[1];
      } else {
        plan.next_node = goal_node;
      }
      plan.turn_queue = graph_.build_turn_queue(plan.path_nodes, straight_threshold_deg_);

      RCLCPP_WARN(
        get_logger(),
        "Falling back to nearest-node planning from %s because no aligned current edge was found",
        start_node.c_str());
    }

    publish_plan(plan);
  }

  void publish_plan(const RoutePlan & plan)
  {
    if (!plan.found) {
      return;
    }

    std_msgs::msg::String next_node_msg;
    next_node_msg.data = plan.next_node;
    next_node_pub_->publish(next_node_msg);

    std_msgs::msg::String path_msg;
    path_msg.data = join_strings(plan.path_nodes, " -> ");
    path_pub_->publish(path_msg);

    std_msgs::msg::Int32MultiArray turn_msg;
    for (const int turn : plan.turn_queue) {
      turn_msg.data.push_back(turn);
    }
    turn_queue_pub_->publish(turn_msg);

    RCLCPP_INFO(
      get_logger(),
      "Goal node: %s | Next node: %s | Path: %s",
      plan.goal_node.c_str(), plan.next_node.c_str(), path_msg.data.c_str());
    RCLCPP_INFO(get_logger(), "Turn queue: [%s]", join_turns(plan.turn_queue).c_str());
  }

  RoadGraph graph_;
  PoseState current_pose_;
  PoseState target_pose_;

  double max_edge_snap_distance_{400.0};
  double max_heading_error_deg_{60.0};
  double straight_threshold_deg_{25.0};

  rclcpp::Subscription<geometry_msgs::msg::Pose2D>::SharedPtr current_pose_sub_;
  rclcpp::Subscription<geometry_msgs::msg::Pose2D>::SharedPtr target_pose_sub_;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr next_node_pub_;
  rclcpp::Publisher<std_msgs::msg::Int32MultiArray>::SharedPtr turn_queue_pub_;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr path_pub_;
};

}  // namespace

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<MapPlannerNode>());
  rclcpp::shutdown();
  return 0;
}
