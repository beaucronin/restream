resource "aws_dynamodb_table" "message_cache" {
	name = "${var.message_cache_table}"
	read_capacity = 5
	write_capacity = 5
	hash_key = "ChannelItemId"
	# range_key = "Timestamp"
	stream_enabled = true
	stream_view_type = "NEW_IMAGE"
	attribute {
		name = "ChannelItemId"
		type = "S"
	}
	# attribute {
	# 	name = "Timestamp"
	# 	type = "S"
	# }
}
