import asyncio
import os

from dotenv import load_dotenv

from travel_companion.agents.food_agent import FoodAgent
from travel_companion.models.external import (
    GeoapifyCateringCategory,
    RestaurantSearchRequest,
)


async def interactive_test(agent: FoodAgent):
    print("\nCommands: 'quit' to exit, 'cuisine <city>' for cuisine search")

    while True:
        user_input = input("\nEnter city name (or command): ").strip()

        if user_input.lower() in ["quit", "exit", "q"]:
            break

        if not user_input:
            continue

        if user_input.lower().startswith("cuisine "):
            city = user_input[8:].strip()
            if not city:
                print("Please specify a city after 'cuisine'")
                continue

            print(f"\nAvailable cuisines for {city}:")
            cuisines = [
                ("1", "Italian", GeoapifyCateringCategory.RESTAURANT_ITALIAN),
                ("2", "Chinese", GeoapifyCateringCategory.RESTAURANT_CHINESE),
                ("3", "Japanese", GeoapifyCateringCategory.RESTAURANT_JAPANESE),
                ("4", "Mexican", GeoapifyCateringCategory.RESTAURANT_MEXICAN),
                ("5", "Thai", GeoapifyCateringCategory.RESTAURANT_THAI),
                ("6", "Fast Food", GeoapifyCateringCategory.FAST_FOOD),
                ("7", "Pizza", GeoapifyCateringCategory.RESTAURANT_PIZZA),
                ("8", "Cafes", GeoapifyCateringCategory.CAFE),
            ]

            for num, name, _ in cuisines:
                print(f"{num}. {name}")

            choice = input("Choose cuisine (1-8): ").strip()
            try:
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(cuisines):
                    _, cuisine_name, cuisine_category = cuisines[choice_idx]
                    print(f"\n🍽️  Searching for {cuisine_name} restaurants in {city}...")

                    response = await agent.search_by_cuisine(
                        location=city,
                        cuisine_category=cuisine_category,
                        radius_meters=5000,
                        max_results=5,
                    )

                    print(f"\n✅ Found {len(response.restaurants)} {cuisine_name} restaurants")
                    print(f"⏱️  Search time: {response.search_time_ms}ms")
                    print(f"📦 Cached: {response.cached}\n")

                    for i, restaurant in enumerate(response.restaurants, 1):
                        print(f"{i}. {restaurant.name}")
                        print(f"   📍 {restaurant.location.address_line2}")
                        if restaurant.distance_meters:
                            print(f"   📏 Distance: {restaurant.distance_meters}m")
                        if restaurant.categories:
                            print(f"   🏷️  Categories: {', '.join(restaurant.categories)}")
                        print()
                else:
                    print("Invalid choice")
            except ValueError:
                print("Please enter a number")
        else:
            # Regular city search
            city = user_input
            print(f"\n🔍 Searching for restaurants in {city}...")

            search_request = RestaurantSearchRequest(
                location=city,
                radius_meters=5000,
                max_results=5,
            )

            response = await agent.search_restaurants(search_request)

            print(f"\n✅ Found {len(response.restaurants)} restaurants")
            print(f"⏱️  Search time: {response.search_time_ms}ms")
            print(f"📦 Cached: {response.cached}\n")

            for i, restaurant in enumerate(response.restaurants, 1):
                print(f"{i}. {restaurant.name}")
                print(f"   📍 {restaurant.location.address_line2}")
                if restaurant.distance_meters:
                    print(f"   📏 Distance: {restaurant.distance_meters}m")
                if restaurant.categories:
                    print(f"   🏷️  Categories: {', '.join(restaurant.categories)}")
                print()


async def main():
    load_dotenv()
    api_key = os.getenv("GEOAPIFY_API_KEY")
    if not api_key:
        print("E: GEOAPIFY_API_KEY not found")
        return

    agent = FoodAgent()

    await interactive_test(agent)


if __name__ == "__main__":
    asyncio.run(main())
