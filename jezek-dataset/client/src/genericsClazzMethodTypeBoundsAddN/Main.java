package genericsClazzMethodTypeBoundsAddN;

import testing_lib.genericsClazzMethodTypeBoundsAddN.GenericsClazzMethodTypeBoundsAddN;

public class Main extends GenericsClazzMethodTypeBoundsAddN {


	public static void main(String[] args) {
		
		GenericsClazzMethodTypeBoundsAddN constr = new GenericsClazzMethodTypeBoundsAddN();
		constr.<Object>method1();
		
	}

	@Override
	public <T> void method1() {

	}
	
}
