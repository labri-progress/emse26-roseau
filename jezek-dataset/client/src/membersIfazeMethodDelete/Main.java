package membersIfazeMethodDelete;

import testing_lib.membersIfazeMethodDelete.MembersIfazeMethodDelete;

public class Main implements MembersIfazeMethodDelete {

	@Override
	public void method1() {

	}

	public static void main(String[] args) {
		MembersIfazeMethodDelete x = new Main();
		x.method1(); // <-- key: invokevirtual resolved against MembersIfazeMethodDelete
	}

}
