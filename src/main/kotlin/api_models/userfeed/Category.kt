package api_models.userfeed

data class Category(
    val markNumber: Int,
    val mood: String,
    val percent: Double,
    val studentCount: Int,
    val value: String
)